from datetime import datetime, timedelta
from math import ceil

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import and_, or_

from ..crm.auth import requiere_rol
from ..extensions import db
from ..docs import documentar, ruta_id
from ..observer import bus_ordenes
from ..scm.models import CarritoItem, Producto
from ..scm.routes import carrito_de
from ..scm.stock import StockInsuficiente
from ..utils import error
from .clave import BLOQUEO_MINUTOS, MAX_INTENTOS, bloqueada, clave_valida
from .estados import CANCELADA, ENTREGADA, EN_CAMINO, PREPARANDO, TransicionInvalida, validar_transicion
from .evaluacion import resumen_estrellas, validar_comentario, validar_estrellas
from .factura import emitir_factura
from .models import EvaluacionProducto, EvaluacionVendedor, Orden, ItemOrden
from .permisos import puede_fijar

bp = Blueprint("erp", __name__)


@bp.get("/ordenes")
@requiere_rol()
@documentar("GET", "/api/ordenes", "Listar órdenes según el perfil", ["ERP"],
            descripcion="Comprador: sus compras. Vendedor: ventas con sus productos. Repartidor: pedidos listos para recoger y los suyos.",
            respuestas={200: ("Lista de órdenes", "[]OrdenDTO"), 401: ("Sin sesión", "ErrorDTO")})
def listar_ordenes(u):
    q = Orden.query
    if u.rol == "consumidor":
        q = q.filter(Orden.consumidor_id == u.id)
    elif u.rol == "vendedor":
        q = q.join(ItemOrden).join(Producto).filter(Producto.vendedor_id == u.id)
    else:
        q = q.filter(or_(Orden.repartidor_id == u.id,
                         and_(Orden.repartidor_id.is_(None), Orden.estado == PREPARANDO)))
    return jsonify([o.to_dict(u) for o in q.order_by(Orden.id.desc()).distinct()])


@bp.post("/ordenes")
@requiere_rol("consumidor")
@documentar("POST", "/api/ordenes", "Crear orden a partir del carrito (comprador)", ["ERP"],
            body="CrearOrdenDTO",
            descripcion="Descuenta stock, emite la factura y genera la clave de entrega.",
            respuestas={201: ("Orden creada", "OrdenDTO"),
                        400: ("Carrito vacío o ubicación faltante", "ErrorDTO"),
                        401: ("Sin sesión", "ErrorDTO"),
                        409: ("Stock insuficiente", "ErrorDTO")})
def crear_orden(u):
    d = request.get_json(force=True)
    if not d.get("ubicacion_entrega"):
        return error("indica dónde quieres recibir tu pedido")
    carrito, filas = carrito_de(u.id)
    if carrito.esta_vacio():
        return error("el carrito está vacío")

    orden = Orden(consumidor_id=u.id, ubicacion_entrega=d["ubicacion_entrega"])
    try:
        for f in filas:
            f.producto.inventario.reservar(f.cantidad)
            orden.items.append(ItemOrden(producto_id=f.producto_id, cantidad=f.cantidad,
                                         precio_unitario=f.producto.precio))
    except StockInsuficiente as e:
        db.session.rollback()
        return error(f"{f.producto.nombre}: {e}", 409)

    db.session.add(orden)
    db.session.flush()
    emitir_factura(orden, carrito.subtotal(), d.get("metodo_pago", "efectivo"),
                   current_app.config["COMISION_PORCENTAJE"])
    CarritoItem.query.filter_by(usuario_id=u.id).delete()
    db.session.flush()
    bus_ordenes.notificar(orden, orden.estado)
    db.session.commit()
    return jsonify(orden.to_dict(u)), 201


@bp.post("/ordenes/<int:oid>/repartidor")
@requiere_rol("repartidor")
@documentar("POST", "/api/ordenes/{oid}/repartidor", "Tomar una entrega (repartidor)", ["ERP"],
            parametros=[ruta_id("oid", "ID de la orden")],
            respuestas={200: ("Entrega asignada", "OrdenDTO"),
                        403: ("Solo los repartidores", "ErrorDTO"),
                        409: ("Ya tiene repartidor o aún no está lista", "ErrorDTO")})
def tomar_entrega(u, oid):
    orden = db.get_or_404(Orden, oid)
    if orden.repartidor_id:
        return error("la orden ya tiene repartidor", 409)
    if orden.estado != PREPARANDO:
        return error("la orden aún no está lista para recoger", 409)
    orden.repartidor_id = u.id
    db.session.commit()
    return jsonify(orden.to_dict(u))


@bp.patch("/ordenes/<int:oid>/estado")
@requiere_rol()
@documentar("PATCH", "/api/ordenes/{oid}/estado", "Cambiar el estado de una orden", ["ERP"],
            body="CambiarEstadoDTO", parametros=[ruta_id("oid", "ID de la orden")],
            descripcion="Comprador: cancelar. Vendedor: preparar o cancelar. Repartidor: en_camino y entregada (con la clave del comprador).",
            respuestas={200: ("Estado actualizado", "OrdenDTO"),
                        403: ("Rol no permitido o clave de entrega incorrecta", "ErrorDTO"),
                        409: ("Transición de estado inválida", "ErrorDTO"),
                        429: ("Demasiados intentos con la clave", "ErrorDTO")})
def cambiar_estado(u, oid):
    orden = db.get_or_404(Orden, oid)
    d = request.get_json(force=True)
    nuevo = d.get("estado")

    es_participante = (
        (u.rol == "consumidor" and orden.consumidor_id == u.id)
        or (u.rol == "vendedor" and any(i.producto.vendedor_id == u.id for i in orden.items))
        or (u.rol == "repartidor" and orden.repartidor_id == u.id)
    )
    if not es_participante or not puede_fijar(u.rol, nuevo):
        return error("no puedes hacer este cambio", 403)
    try:
        validar_transicion(orden.estado, nuevo)
    except TransicionInvalida as e:
        return error(str(e), 409)
    if nuevo == EN_CAMINO and not orden.repartidor_id:
        return error("asigna un repartidor antes de enviar", 409)
    if nuevo == ENTREGADA:
        ahora = datetime.utcnow()
        if bloqueada(orden.bloqueo_clave_hasta, ahora):
            mins = ceil((orden.bloqueo_clave_hasta - ahora).total_seconds() / 60)
            return error(f"demasiados intentos; vuelve a intentar en {mins} min", 429)
        if not clave_valida(orden.clave_entrega, d.get("clave")):
            orden.intentos_clave += 1
            if orden.intentos_clave >= MAX_INTENTOS:
                orden.intentos_clave = 0
                orden.bloqueo_clave_hasta = ahora + timedelta(minutes=BLOQUEO_MINUTOS)
            db.session.commit()
            return error("clave de entrega incorrecta", 403)
    if nuevo == CANCELADA:
        for i in orden.items:
            i.producto.inventario.reponer(i.cantidad)
    orden.estado = nuevo
    bus_ordenes.notificar(orden, nuevo)
    db.session.commit()
    return jsonify(orden.to_dict(u))


@bp.get("/ordenes/<int:oid>/factura")
@requiere_rol()
def ver_factura(u, oid):
    orden = db.get_or_404(Orden, oid)
    if u.id not in {orden.consumidor_id, orden.repartidor_id} | {i.producto.vendedor_id for i in orden.items}:
        return error("no tienes acceso a esta factura", 403)
    return jsonify({"orden_id": orden.id, **orden.factura.to_dict()})


@bp.post("/ordenes/<int:oid>/evaluaciones")
@requiere_rol("consumidor")
@documentar("POST", "/api/ordenes/{oid}/evaluaciones", "Evaluar producto y vendedor de una compra entregada", ["ERP"],
            body="EvaluarCompraDTO", parametros=[ruta_id("oid", "ID de la orden")],
            respuestas={201: ("Evaluación registrada", "OrdenDTO"),
                        400: ("Estrellas o datos inválidos", "ErrorDTO"),
                        403: ("No es tu compra", "ErrorDTO"),
                        409: ("Aún no entregada o ya evaluada", "ErrorDTO")})
def evaluar_compra(u, oid):
    orden = db.get_or_404(Orden, oid)
    if orden.consumidor_id != u.id:
        return error("no es tu compra", 403)
    if orden.estado != ENTREGADA:
        return error("podrás evaluar cuando recibas tu pedido", 409)
    d = request.get_json(force=True)
    productos, vendedores = d.get("productos") or [], d.get("vendedores") or []
    if not productos and not vendedores:
        return error("elige al menos una calificación")

    items = {i.id: i for i in orden.items}
    vendedores_orden = {i.producto.vendedor_id for i in orden.items}
    ya_vendedores = {e.vendedor_id for e in orden.evaluaciones_vendedor}
    nuevos, vistos_i, vistos_v = [], set(), set()
    try:
        for x in productos:
            item = items.get(x.get("item_id"))
            if not item:
                return error("ese producto no pertenece a tu compra", 404)
            if item.evaluacion or item.id in vistos_i:
                return error(f"ya evaluaste {item.producto.nombre}", 409)
            vistos_i.add(item.id)
            nuevos.append(EvaluacionProducto(
                item_orden_id=item.id, producto_id=item.producto_id, consumidor_id=u.id,
                estrellas=validar_estrellas(x.get("estrellas")), comentario=validar_comentario(x.get("comentario"))))
        for x in vendedores:
            vid = x.get("vendedor_id")
            if vid not in vendedores_orden:
                return error("ese vendedor no pertenece a tu compra", 404)
            if vid in ya_vendedores or vid in vistos_v:
                return error("ya evaluaste a ese vendedor", 409)
            vistos_v.add(vid)
            nuevos.append(EvaluacionVendedor(
                orden_id=orden.id, vendedor_id=vid, consumidor_id=u.id,
                estrellas=validar_estrellas(x.get("estrellas")), comentario=validar_comentario(x.get("comentario"))))
    except ValueError as e:
        return error(str(e))
    db.session.add_all(nuevos)
    db.session.commit()
    return jsonify(orden.to_dict(u)), 201


@bp.get("/productos/<int:pid>/evaluaciones")
@requiere_rol()
def opiniones_producto(u, pid):
    p = db.get_or_404(Producto, pid)
    evs = EvaluacionProducto.query.filter_by(producto_id=pid).order_by(EvaluacionProducto.id.desc()).limit(50)
    ficha = p.to_dict()
    return jsonify({
        "producto": p.nombre, "calificacion": ficha["calificacion"],
        "vendedor": p.vendedor.nombre, "vendedor_calificacion": ficha["vendedor_calificacion"],
        "opiniones": [{"estrellas": e.estrellas, "comentario": e.comentario,
                       "consumidor": e.consumidor.nombre.split()[0], "fecha": e.creada_en.isoformat()} for e in evs],
    })

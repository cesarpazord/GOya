from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import and_, or_

from ..crm.auth import requiere_rol
from ..extensions import db
from ..observer import bus_ordenes
from ..scm.models import CarritoItem, Producto
from ..scm.routes import carrito_de
from ..scm.stock import StockInsuficiente
from ..utils import error
from .estados import CANCELADA, EN_CAMINO, PREPARANDO, TransicionInvalida, validar_transicion
from .factura import emitir_factura
from .models import Orden, ItemOrden
from .permisos import puede_fijar

bp = Blueprint("erp", __name__)


@bp.get("/ordenes")
@requiere_rol()
def listar_ordenes(u):
    q = Orden.query
    if u.rol == "consumidor":
        q = q.filter(Orden.consumidor_id == u.id)
    elif u.rol == "vendedor":
        q = q.join(ItemOrden).join(Producto).filter(Producto.vendedor_id == u.id)
    else:
        q = q.filter(or_(Orden.repartidor_id == u.id,
                         and_(Orden.repartidor_id.is_(None), Orden.estado == PREPARANDO)))
    return jsonify([o.to_dict() for o in q.order_by(Orden.id.desc()).distinct()])


@bp.post("/ordenes")
@requiere_rol("consumidor")
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
    return jsonify(orden.to_dict()), 201


@bp.post("/ordenes/<int:oid>/repartidor")
@requiere_rol("repartidor")
def tomar_entrega(u, oid):
    orden = db.get_or_404(Orden, oid)
    if orden.repartidor_id:
        return error("la orden ya tiene repartidor", 409)
    if orden.estado != PREPARANDO:
        return error("la orden aún no está lista para recoger", 409)
    orden.repartidor_id = u.id
    db.session.commit()
    return jsonify(orden.to_dict())


@bp.patch("/ordenes/<int:oid>/estado")
@requiere_rol()
def cambiar_estado(u, oid):
    orden = db.get_or_404(Orden, oid)
    nuevo = request.get_json(force=True).get("estado")

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
    if nuevo == CANCELADA:
        for i in orden.items:
            i.producto.inventario.reponer(i.cantidad)
    orden.estado = nuevo
    bus_ordenes.notificar(orden, nuevo)
    db.session.commit()
    return jsonify(orden.to_dict())


@bp.get("/ordenes/<int:oid>/factura")
@requiere_rol()
def ver_factura(u, oid):
    orden = db.get_or_404(Orden, oid)
    if u.id not in {orden.consumidor_id, orden.repartidor_id} | {i.producto.vendedor_id for i in orden.items}:
        return error("no tienes acceso a esta factura", 403)
    return jsonify({"orden_id": orden.id, **orden.factura.to_dict()})

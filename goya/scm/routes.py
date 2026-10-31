from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from ..crm.auth import requiere_rol
from ..extensions import db
from ..docs import documentar, ruta_id
from ..uploads import EXT_FOTO, guardar
from ..utils import error
from .carrito import Carrito
from .models import Producto, Inventario, CarritoItem
from .stock import StockInsuficiente

bp = Blueprint("scm", __name__)


def carrito_de(uid):
    filas = CarritoItem.query.filter_by(usuario_id=uid).order_by(CarritoItem.id).all()
    c = Carrito()
    for f in filas:
        c.agregar(f.producto_id, f.producto.precio, f.cantidad, f.producto.nombre)
    return c, filas


def carrito_json(uid):
    c, filas = carrito_de(uid)
    fotos = {f.producto_id: f.producto.foto for f in filas}
    return jsonify({"items": [{**i, "precio": float(i["precio"]), "foto": f"/api/media/fotos/{fotos[i['producto_id']]}"}
                              for i in c.items()],
                    "subtotal": float(c.subtotal())})


@bp.get("/media/fotos/<nombre>")
def foto(nombre):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"] + "/fotos", nombre)


@bp.get("/productos")
@requiere_rol()
@documentar("GET", "/api/productos", "Listar productos", ["SCM"],
            descripcion="Comprador y repartidor: productos con stock. Vendedor: solo los suyos.",
            respuestas={200: ("Lista de productos", "[]ProductoDTO"), 401: ("Sin sesión", "ErrorDTO")})
def listar_productos(u):
    q = Producto.query.join(Inventario).filter(Producto.activo.is_(True)).order_by(Producto.id.desc())
    if u.rol == "vendedor":
        q = q.filter(Producto.vendedor_id == u.id)
    else:
        q = q.filter(Inventario.cantidad > 0)
    return jsonify([p.to_dict() for p in q])


@bp.post("/productos")
@requiere_rol("vendedor")
@documentar("POST", "/api/productos", "Publicar un producto (vendedor)", ["SCM"],
            body="CrearProductoDTO", body_tipo="multipart/form-data",
            respuestas={201: ("Producto publicado", "ProductoDTO"),
                        400: ("Datos o foto inválidos", "ErrorDTO"),
                        401: ("Sin sesión", "ErrorDTO"),
                        403: ("Solo los vendedores pueden publicar", "ErrorDTO")})
def crear_producto(u):
    d = request.form
    try:
        precio = Decimal(d["precio"])
        stock = int(d["cantidad"])
        nombre, desc, ubic = d["nombre"].strip(), d["descripcion"].strip(), d["ubicacion_venta"].strip()
    except (KeyError, ValueError, InvalidOperation):
        return error("nombre, descripción, precio, cantidad y ubicación son obligatorios")
    if not (nombre and desc and ubic):
        return error("nombre, descripción y ubicación no pueden estar vacíos")
    if precio < 0 or stock < 0:
        return error("precio y cantidad no pueden ser negativos")
    try:
        foto_nombre = guardar(request.files.get("foto"), "fotos", EXT_FOTO, current_app.config["UPLOAD_FOLDER"])
    except ValueError as e:
        return error("foto: " + str(e))
    p = Producto(vendedor_id=u.id, nombre=nombre, descripcion=desc, foto=foto_nombre,
                 precio=precio, ubicacion_venta=ubic)
    p.inventario = Inventario(cantidad=stock)
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@bp.put("/productos/<int:pid>")
@requiere_rol("vendedor")
def editar_producto(u, pid):
    p = db.get_or_404(Producto, pid)
    if p.vendedor_id != u.id or not p.activo:
        return error("no es tu producto", 403)
    d = request.form
    try:
        nombre, desc, ubic = d["nombre"].strip(), d["descripcion"].strip(), d["ubicacion_venta"].strip()
        precio, stock = Decimal(d["precio"]), int(d["cantidad"])
    except (KeyError, ValueError, InvalidOperation):
        return error("nombre, descripción, precio, cantidad y ubicación son obligatorios")
    if not (nombre and desc and ubic):
        return error("nombre, descripción y ubicación no pueden estar vacíos")
    if precio < 0 or stock < 0:
        return error("precio y cantidad no pueden ser negativos")
    nueva = request.files.get("foto")
    if nueva is not None and nueva.filename:
        try:
            p.foto = guardar(nueva, "fotos", EXT_FOTO, current_app.config["UPLOAD_FOLDER"])
        except ValueError as e:
            return error("foto: " + str(e))
    p.nombre, p.descripcion, p.ubicacion_venta, p.precio = nombre, desc, ubic, precio
    p.inventario.cantidad = stock
    db.session.commit()
    return jsonify(p.to_dict())


@bp.delete("/productos/<int:pid>")
@requiere_rol("vendedor")
def eliminar_producto(u, pid):
    p = db.get_or_404(Producto, pid)
    if p.vendedor_id != u.id or not p.activo:
        return error("no es tu producto", 403)
    p.activo = False
    CarritoItem.query.filter_by(producto_id=p.id).delete()
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/productos/<int:pid>/reponer")
@requiere_rol("vendedor")
def reponer_stock(u, pid):
    p = db.get_or_404(Producto, pid)
    if p.vendedor_id != u.id or not p.activo:
        return error("no es tu producto", 403)
    try:
        p.inventario.reponer(int(request.get_json(force=True).get("cantidad", 0)))
    except ValueError as e:
        return error(str(e))
    db.session.commit()
    return jsonify(p.to_dict())


@bp.get("/carrito")
@requiere_rol("consumidor")
def ver_carrito(u):
    return carrito_json(u.id)


@bp.post("/carrito")
@requiere_rol("consumidor")
@documentar("POST", "/api/carrito", "Agregar un producto al carrito (comprador)", ["SCM"],
            body="CarritoItemDTO",
            respuestas={200: ("Carrito actualizado", "CarritoDTO"),
                        400: ("Cantidad inválida o stock insuficiente", "ErrorDTO"),
                        404: ("Producto no encontrado", "ErrorDTO"),
                        403: ("Solo los compradores tienen carrito", "ErrorDTO")})
def agregar_al_carrito(u):
    d = request.get_json(force=True)
    p = db.session.get(Producto, d.get("producto_id"))
    if not p or not p.activo:
        return error("producto no encontrado", 404)
    try:
        cant = int(d.get("cantidad", 1))
        if cant < 1:
            raise ValueError("cantidad debe ser mayor a 0")
        fila = CarritoItem.query.filter_by(usuario_id=u.id, producto_id=p.id).first()
        total = cant + (fila.cantidad if fila else 0)
        if total > p.inventario.cantidad:
            raise StockInsuficiente(f"solo quedan {p.inventario.cantidad} unidades")
    except ValueError as e:
        return error(str(e))
    if fila:
        fila.cantidad = total
    else:
        db.session.add(CarritoItem(usuario_id=u.id, producto_id=p.id, cantidad=cant))
    db.session.commit()
    return carrito_json(u.id)


@bp.delete("/carrito/<int:pid>")
@requiere_rol("consumidor")
def quitar_del_carrito(u, pid):
    CarritoItem.query.filter_by(usuario_id=u.id, producto_id=pid).delete()
    db.session.commit()
    return carrito_json(u.id)

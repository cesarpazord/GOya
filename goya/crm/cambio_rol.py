"""CRM · Cambio de perfil: reglas que aplican al aprobar una solicitud."""


def ordenes_en_curso(u):
    from ..erp.models import Orden, ItemOrden
    from ..scm.models import Producto

    activas = Orden.query.filter(Orden.estado.notin_(["entregada", "cancelada"]))
    if u.rol == "consumidor":
        return activas.filter(Orden.consumidor_id == u.id).count()
    if u.rol == "repartidor":
        return activas.filter(Orden.repartidor_id == u.id).count()
    return activas.join(ItemOrden).join(Producto).filter(Producto.vendedor_id == u.id).count()


def aplicar_cambio(u, nuevo):
    from ..scm.models import CarritoItem, Producto

    if u.rol == "consumidor":
        CarritoItem.query.filter_by(usuario_id=u.id).delete()
    if u.rol == "vendedor":
        for p in Producto.query.filter_by(vendedor_id=u.id, activo=True):
            p.activo = False
            CarritoItem.query.filter_by(producto_id=p.id).delete()
    u.rol = nuevo

"""Notificaciones: observador que avisa a consumidor, vendedores y repartidor."""
from datetime import datetime

from flask import Blueprint, jsonify

from ..crm.auth import requiere_rol
from ..extensions import db
from . import Observador, bus_ordenes

bp = Blueprint("notificaciones", __name__)

MENSAJES = {
    "creada": "La orden #{id} fue creada.",
    "preparando": "La orden #{id} se está preparando.",
    "en_camino": "La orden #{id} va en camino.",
    "entregada": "La orden #{id} fue entregada.",
    "cancelada": "La orden #{id} fue cancelada.",
}


class Notificacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    orden_id = db.Column(db.Integer, db.ForeignKey("orden.id"), nullable=False)
    mensaje = db.Column(db.String(255), nullable=False)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "orden_id": self.orden_id, "mensaje": self.mensaje,
                "creada_en": self.creada_en.isoformat()}


def actores_de(orden):
    actores = {orden.consumidor_id} | {i.producto.vendedor_id for i in orden.items}
    if orden.repartidor_id:
        actores.add(orden.repartidor_id)
    return actores


class NotificadorDeActores(Observador):
    def actualizar(self, orden, estado):
        texto = MENSAJES[estado].format(id=orden.id)
        for uid in actores_de(orden):
            db.session.add(Notificacion(usuario_id=uid, orden_id=orden.id, mensaje=texto))


notificador = NotificadorDeActores()


def registrar_observadores():
    bus_ordenes.suscribir(notificador)


@bp.get("/notificaciones")
@requiere_rol()
def listar_notificaciones(u):
    q = Notificacion.query.filter_by(usuario_id=u.id).order_by(Notificacion.id.desc())
    return jsonify([n.to_dict() for n in q.limit(50)])

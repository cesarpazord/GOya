from datetime import datetime

from ..extensions import db
from .clave import generar_clave
from .estados import CREADA


class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consumidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    repartidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    ubicacion_entrega = db.Column(db.String(160), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default=CREADA)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    clave_entrega = db.Column(db.String(6), nullable=False, default=generar_clave)
    intentos_clave = db.Column(db.Integer, nullable=False, default=0)
    bloqueo_clave_hasta = db.Column(db.DateTime)

    consumidor = db.relationship("Usuario", foreign_keys=[consumidor_id])
    repartidor = db.relationship("Usuario", foreign_keys=[repartidor_id])
    items = db.relationship("ItemOrden", backref="orden", cascade="all, delete-orphan")
    factura = db.relationship("Factura", uselist=False, backref="orden", cascade="all, delete-orphan")
    evaluaciones_vendedor = db.relationship("EvaluacionVendedor", backref="orden", cascade="all, delete-orphan")

    def to_dict(self, viewer=None):
        d = {
            "id": self.id,
            "consumidor": self.consumidor.nombre,
            "repartidor": self.repartidor.nombre if self.repartidor else None,
            "destino": self.ubicacion_entrega,
            "origenes": sorted({i.producto.ubicacion_venta for i in self.items}),
            "estado": self.estado,
            "creada_en": self.creada_en.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "factura": self.factura.to_dict() if self.factura else None,
            "vendedores": [{"id": v.id, "nombre": v.nombre}
                           for v in sorted({i.producto.vendedor for i in self.items}, key=lambda x: x.id)],
            "evaluaciones_vendedor": [e.to_dict() for e in self.evaluaciones_vendedor],
        }
        # La clave solo la ve el comprador, mientras el pedido siga en curso.
        if viewer is not None and viewer.id == self.consumidor_id and self.estado not in ("entregada", "cancelada"):
            d["clave_entrega"] = self.clave_entrega
        return d


class ItemOrden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("orden.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    producto = db.relationship("Producto")
    evaluacion = db.relationship("EvaluacionProducto", uselist=False, backref="item", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "producto_id": self.producto_id, "vendedor_id": self.producto.vendedor_id,
                "evaluacion": self.evaluacion.to_dict() if self.evaluacion else None,
                "producto": self.producto.nombre, "foto": f"/api/media/fotos/{self.producto.foto}",
                "vendedor": self.producto.vendedor.nombre, "cantidad": self.cantidad,
                "precio_unitario": float(self.precio_unitario)}


class Factura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("orden.id"), unique=True, nullable=False)
    folio = db.Column(db.String(20), unique=True, nullable=False)
    metodo_pago = db.Column(db.String(30), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    comision = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    emitida_en = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"folio": self.folio, "metodo_pago": self.metodo_pago,
                "subtotal": float(self.subtotal), "comision": float(self.comision),
                "total": float(self.total), "emitida_en": self.emitida_en.isoformat()}


class EvaluacionProducto(db.Model):
    """Calificación de un producto comprado (una por ítem de orden)."""
    id = db.Column(db.Integer, primary_key=True)
    item_orden_id = db.Column(db.Integer, db.ForeignKey("item_orden.id"), unique=True, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    consumidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    estrellas = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.String(300), nullable=False, default="")
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    consumidor = db.relationship("Usuario")

    def to_dict(self):
        return {"estrellas": self.estrellas, "comentario": self.comentario}


class EvaluacionVendedor(db.Model):
    """Calificación del vendedor de una compra (una por vendedor y orden)."""
    __table_args__ = (db.UniqueConstraint("orden_id", "vendedor_id"),)
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("orden.id"), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    consumidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    estrellas = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.String(300), nullable=False, default="")
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    vendedor = db.relationship("Usuario", foreign_keys=[vendedor_id])

    def to_dict(self):
        return {"vendedor_id": self.vendedor_id, "vendedor": self.vendedor.nombre,
                "estrellas": self.estrellas, "comentario": self.comentario}

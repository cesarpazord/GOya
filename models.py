from datetime import datetime

from ..extensions import db
from .estados import CREADA


class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consumidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    repartidor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    ubicacion_entrega = db.Column(db.String(160), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default=CREADA)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)

    consumidor = db.relationship("Usuario", foreign_keys=[consumidor_id])
    repartidor = db.relationship("Usuario", foreign_keys=[repartidor_id])
    items = db.relationship("ItemOrden", backref="orden", cascade="all, delete-orphan")
    factura = db.relationship("Factura", uselist=False, backref="orden", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "consumidor": self.consumidor.nombre,
            "repartidor": self.repartidor.nombre if self.repartidor else None,
            "destino": self.ubicacion_entrega,
            "origenes": sorted({i.producto.ubicacion_venta for i in self.items}),
            "estado": self.estado,
            "creada_en": self.creada_en.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "factura": self.factura.to_dict() if self.factura else None,
        }


class ItemOrden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("orden.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    producto = db.relationship("Producto")

    def to_dict(self):
        return {"producto": self.producto.nombre, "foto": f"/api/media/fotos/{self.producto.foto}",
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

from ..extensions import db
from . import stock as reglas


class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    foto = db.Column(db.String(120), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    ubicacion_venta = db.Column(db.String(160), nullable=False)
    vendedor = db.relationship("Usuario")
    inventario = db.relationship("Inventario", uselist=False, backref="producto", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "vendedor_id": self.vendedor_id, "vendedor": self.vendedor.nombre,
                "nombre": self.nombre, "descripcion": self.descripcion,
                "foto": f"/api/media/fotos/{self.foto}", "precio": float(self.precio),
                "ubicacion_venta": self.ubicacion_venta, "stock": self.inventario.cantidad}


class Inventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), unique=True, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)

    def reservar(self, n):
        self.cantidad = reglas.reservar(self.cantidad, n)

    def reponer(self, n):
        self.cantidad = reglas.reponer(self.cantidad, n)


class CarritoItem(db.Model):
    __table_args__ = (db.UniqueConstraint("usuario_id", "producto_id"),)
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    producto = db.relationship("Producto")

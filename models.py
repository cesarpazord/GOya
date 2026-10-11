from ..extensions import db


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    documento_estudiante = db.Column(db.String(120), nullable=False)
    perfil = db.relationship("Perfil", uselist=False, backref="usuario", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "correo": self.correo, "rol": self.rol,
                "perfil": self.perfil.to_dict() if self.perfil else None}


class Perfil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), unique=True, nullable=False)
    telefono = db.Column(db.String(30))
    facultad = db.Column(db.String(120), default="Facultad de Ingeniería")
    ubicacion_habitual = db.Column(db.String(160))

    def to_dict(self):
        return {"telefono": self.telefono, "facultad": self.facultad,
                "ubicacion_habitual": self.ubicacion_habitual}

from datetime import datetime

from ..extensions import db


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    documento_estudiante = db.Column(db.String(120), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    perfil = db.relationship("Perfil", uselist=False, backref="usuario", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "correo": self.correo, "rol": self.rol,
                "estado": self.estado, "perfil": self.perfil.to_dict() if self.perfil else None}


class Perfil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), unique=True, nullable=False)
    telefono = db.Column(db.String(30))
    facultad = db.Column(db.String(120), default="Facultad de Ingeniería")
    ubicacion_habitual = db.Column(db.String(160))

    def to_dict(self):
        return {"telefono": self.telefono, "facultad": self.facultad,
                "ubicacion_habitual": self.ubicacion_habitual}


class SolicitudRol(db.Model):
    """Solicitud de cambio de perfil; la resuelve el administrador."""
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    rol_actual = db.Column(db.String(20), nullable=False)
    rol_solicitado = db.Column(db.String(20), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    resuelta_en = db.Column(db.DateTime)
    usuario = db.relationship("Usuario")

    def to_dict(self):
        return {"id": self.id,
                "usuario": {"id": self.usuario.id, "nombre": self.usuario.nombre, "correo": self.usuario.correo},
                "rol_actual": self.rol_actual, "rol_solicitado": self.rol_solicitado,
                "motivo": self.motivo, "estado": self.estado,
                "creada_en": self.creada_en.isoformat(),
                "resuelta_en": self.resuelta_en.isoformat() if self.resuelta_en else None}

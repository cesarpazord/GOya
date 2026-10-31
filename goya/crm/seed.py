"""Cuenta de administrador inicial (configurable por variables de entorno)."""
from ..extensions import db
from .models import Usuario, Perfil
from .seguridad import ADMIN, hash_password


def asegurar_admin(app):
    usuario = app.config["ADMIN_USUARIO"]
    if Usuario.query.filter_by(correo=usuario).first():
        return
    u = Usuario(nombre="Administrador", correo=usuario, rol=ADMIN, estado="aprobado",
                password_hash=hash_password(app.config["ADMIN_PASSWORD"]), documento_estudiante="N/A")
    u.perfil = Perfil()
    db.session.add(u)
    db.session.commit()

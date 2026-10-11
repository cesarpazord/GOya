"""CRM · Sesión: usuario actual y control de acceso por rol."""
from functools import wraps

from flask import session

from ..extensions import db
from ..utils import error
from .models import Usuario


def usuario_actual():
    uid = session.get("uid")
    return db.session.get(Usuario, uid) if uid else None


def requiere_rol(*roles):
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            u = usuario_actual()
            if not u:
                return error("inicia sesión para continuar", 401)
            if roles and u.rol not in roles:
                return error("no tienes permiso para esto", 403)
            return f(u, *args, **kwargs)
        return envoltura
    return decorador

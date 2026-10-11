from flask import Blueprint, current_app, jsonify, request, session

from ..extensions import db
from ..uploads import EXT_DOCUMENTO, guardar
from ..utils import error
from .auth import requiere_rol, usuario_actual
from .models import Usuario, Perfil
from .seguridad import hash_password, verificar_password, validar_password, validar_rol

bp = Blueprint("crm", __name__)


@bp.post("/registro")
def registro():
    d = request.form
    try:
        validar_rol(d.get("rol"))
        validar_password(d.get("password"))
    except ValueError as e:
        return error(str(e))
    if not d.get("nombre") or not d.get("correo"):
        return error("nombre y correo son obligatorios")
    if Usuario.query.filter_by(correo=d["correo"]).first():
        return error("correo ya registrado", 409)
    try:
        doc = guardar(request.files.get("documento"), "documentos", EXT_DOCUMENTO,
                      current_app.config["UPLOAD_FOLDER"])
    except ValueError as e:
        return error("documento de estudiante: " + str(e))

    u = Usuario(nombre=d["nombre"], correo=d["correo"], rol=d["rol"],
                password_hash=hash_password(d["password"]), documento_estudiante=doc)
    u.perfil = Perfil()
    db.session.add(u)
    db.session.commit()
    session["uid"] = u.id
    return jsonify(u.to_dict()), 201


@bp.post("/login")
def login():
    d = request.get_json(force=True)
    u = Usuario.query.filter_by(correo=d.get("correo", "")).first()
    if not u or not verificar_password(d.get("password", ""), u.password_hash):
        return error("correo o contraseña incorrectos", 401)
    session.clear()
    session["uid"] = u.id
    return jsonify(u.to_dict())


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    u = usuario_actual()
    if not u:
        return error("sin sesión", 401)
    return jsonify(u.to_dict())


@bp.put("/perfil")
@requiere_rol()
def actualizar_perfil(u):
    d = request.get_json(force=True)
    u.perfil = u.perfil or Perfil()
    for campo in ("telefono", "facultad", "ubicacion_habitual"):
        if campo in d:
            setattr(u.perfil, campo, d[campo])
    db.session.commit()
    return jsonify(u.to_dict())

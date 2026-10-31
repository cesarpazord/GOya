from flask import Blueprint, current_app, jsonify, request, session

from ..extensions import db
from ..docs import documentar, ruta_id
from ..uploads import EXT_DOCUMENTO, guardar
from ..utils import error
from .auth import requiere_rol, usuario_actual
from .cambio_rol import ordenes_en_curso
from .models import Usuario, Perfil, SolicitudRol
from .seguridad import hash_password, verificar_password, validar_motivo, validar_password, validar_rol

bp = Blueprint("crm", __name__)


@bp.post("/registro")
@documentar("POST", "/api/registro", "Crear cuenta con comprobante de estudiante", ["CRM"],
            body="RegistroDTO", body_tipo="multipart/form-data", sesion=False,
            descripcion="La cuenta queda pendiente hasta que el administrador valide el comprobante.",
            respuestas={201: ("Cuenta creada (pendiente de validación) y sesión iniciada", "UsuarioDTO"),
                        400: ("Datos o documento inválidos", "ErrorDTO"),
                        409: ("El correo ya está registrado", "ErrorDTO")})
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
@documentar("POST", "/api/login", "Iniciar sesión", ["CRM"], body="LoginDTO", sesion=False,
            respuestas={200: ("Sesión iniciada (cookie HttpOnly)", "UsuarioDTO"),
                        401: ("Correo o contraseña incorrectos", "ErrorDTO")})
def login():
    d = request.get_json(force=True)
    u = Usuario.query.filter_by(correo=d.get("correo", "")).first()
    if not u or not verificar_password(d.get("password", ""), u.password_hash):
        return error("correo o contraseña incorrectos", 401)
    session.clear()
    session["uid"] = u.id
    return jsonify(u.to_dict())


@bp.post("/logout")
@documentar("POST", "/api/logout", "Cerrar sesión", ["CRM"], sesion=False,
            respuestas={200: ("Sesión cerrada", "OkDTO")})
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
@documentar("GET", "/api/me", "Perfil del usuario con sesión", ["CRM"],
            respuestas={200: ("Usuario actual", "UsuarioDTO"), 401: ("Sin sesión", "ErrorDTO")})
def me():
    u = usuario_actual()
    if not u:
        return error("sin sesión", 401)
    return jsonify(u.to_dict())


@bp.post("/perfil/solicitud-rol")
@requiere_rol("consumidor", "vendedor", "repartidor")
@documentar("POST", "/api/perfil/solicitud-rol", "Solicitar cambio de perfil (lo aprueba el administrador)", ["CRM"],
            body="SolicitudRolCrearDTO",
            respuestas={201: ("Solicitud creada", "SolicitudRolDTO"),
                        400: ("Perfil o motivo inválidos", "ErrorDTO"),
                        401: ("Sin sesión", "ErrorDTO"),
                        409: ("Ya hay una solicitud pendiente u órdenes en curso", "ErrorDTO")})
def solicitar_cambio_rol(u):
    d = request.get_json(force=True)
    try:
        nuevo = validar_rol(d.get("rol"))
        motivo = validar_motivo(d.get("motivo"))
    except ValueError as e:
        return error(str(e))
    if nuevo == u.rol:
        return error("ya usas ese perfil")
    if SolicitudRol.query.filter_by(usuario_id=u.id, estado="pendiente").first():
        return error("ya tienes una solicitud pendiente", 409)
    if ordenes_en_curso(u):
        return error("termina tus órdenes en curso antes de solicitar el cambio", 409)
    sol = SolicitudRol(usuario_id=u.id, rol_actual=u.rol, rol_solicitado=nuevo, motivo=motivo)
    db.session.add(sol)
    db.session.commit()
    return jsonify(sol.to_dict()), 201


@bp.get("/perfil/solicitud-rol")
@requiere_rol("consumidor", "vendedor", "repartidor")
def mi_solicitud(u):
    sol = SolicitudRol.query.filter_by(usuario_id=u.id).order_by(SolicitudRol.id.desc()).first()
    return jsonify(sol.to_dict() if sol else None)


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

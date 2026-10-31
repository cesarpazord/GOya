import os

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from datetime import datetime

from ..extensions import db
from ..docs import documentar, ruta_id
from ..utils import error
from .auth import requiere_rol
from .cambio_rol import aplicar_cambio, ordenes_en_curso
from .models import Usuario, SolicitudRol
from .seguridad import ADMIN, validar_decision, validar_estado_cuenta

bp = Blueprint("admin", __name__)


def _dto(x):
    return {**x.to_dict(), "documento_url": f"/api/admin/usuarios/{x.id}/documento"}


@bp.get("/admin/usuarios")
@requiere_rol(ADMIN)
def listar_usuarios(u):
    q = Usuario.query.filter(Usuario.rol != ADMIN).order_by(Usuario.id.desc())
    if request.args.get("estado"):
        q = q.filter_by(estado=request.args["estado"])
    return jsonify([_dto(x) for x in q])


@bp.get("/admin/usuarios/<int:uid>/documento")
@requiere_rol(ADMIN)
def documento(u, uid):
    x = db.get_or_404(Usuario, uid)
    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "documentos")
    return send_from_directory(carpeta, x.documento_estudiante)


@bp.post("/admin/usuarios/<int:uid>/estado")
@requiere_rol(ADMIN)
@documentar("POST", "/api/admin/usuarios/{uid}/estado", "Aprobar o rechazar una cuenta de estudiante", ["Admin"],
            body="DecisionCuentaDTO", parametros=[ruta_id("uid", "ID del usuario")],
            respuestas={200: ("Cuenta actualizada", "UsuarioDTO"),
                        400: ("Estado inválido", "ErrorDTO"),
                        403: ("Solo el administrador", "ErrorDTO")})
def decidir(u, uid):
    x = db.get_or_404(Usuario, uid)
    if x.rol == ADMIN:
        return error("no se puede modificar al administrador", 403)
    try:
        x.estado = validar_estado_cuenta(request.get_json(force=True).get("estado"))
    except ValueError as e:
        return error(str(e))
    db.session.commit()
    return jsonify(_dto(x))


@bp.get("/admin/resumen")
@requiere_rol(ADMIN)
def resumen(u):
    return jsonify({
        "cuentas_pendientes": Usuario.query.filter(Usuario.rol != ADMIN, Usuario.estado == "pendiente").count(),
        "solicitudes_pendientes": SolicitudRol.query.filter_by(estado="pendiente").count(),
    })


@bp.get("/admin/solicitudes")
@requiere_rol(ADMIN)
def listar_solicitudes(u):
    q = SolicitudRol.query.order_by(SolicitudRol.id.desc())
    if request.args.get("estado"):
        q = q.filter_by(estado=request.args["estado"])
    return jsonify([s.to_dict() for s in q])


@bp.post("/admin/solicitudes/<int:sid>/decision")
@requiere_rol(ADMIN)
@documentar("POST", "/api/admin/solicitudes/{sid}/decision", "Resolver una solicitud de cambio de perfil", ["Admin"],
            body="DecisionSolicitudDTO", parametros=[ruta_id("sid", "ID de la solicitud")],
            respuestas={200: ("Solicitud resuelta", "SolicitudRolDTO"),
                        400: ("Decisión inválida", "ErrorDTO"),
                        403: ("Solo el administrador", "ErrorDTO"),
                        409: ("Ya resuelta o el usuario tiene órdenes en curso", "ErrorDTO")})
def decidir_solicitud(u, sid):
    sol = db.get_or_404(SolicitudRol, sid)
    if sol.estado != "pendiente":
        return error("la solicitud ya fue resuelta", 409)
    try:
        decision = validar_decision(request.get_json(force=True).get("estado"))
    except ValueError as e:
        return error(str(e))
    if decision == "aprobada":
        if ordenes_en_curso(sol.usuario):
            return error("el usuario tiene órdenes en curso; no se puede aprobar todavía", 409)
        aplicar_cambio(sol.usuario, sol.rol_solicitado)
    sol.estado = decision
    sol.resuelta_en = datetime.utcnow()
    db.session.commit()
    return jsonify(sol.to_dict())

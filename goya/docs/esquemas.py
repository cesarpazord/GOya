"""Esquemas (DTOs) de entrada y salida para OpenAPI 3."""


def obj(props, required=None, descripcion=None):
    d = {"type": "object", "properties": props}
    if required:
        d["required"] = required
    if descripcion:
        d["description"] = descripcion
    return d


def ref(nombre):
    return {"$ref": f"#/components/schemas/{nombre}"}


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}
B = {"type": "boolean"}
FECHA = {"type": "string", "format": "date-time"}
ARCHIVO = {"type": "string", "format": "binary"}


def lista(x):
    return {"type": "array", "items": x}


ESQUEMAS = {
    "ErrorDTO": obj({"error": {**S, "example": "mensaje explicando qué salió mal"}}, ["error"]),
    "OkDTO": obj({"ok": {**B, "example": True}}),

    # ---------- CRM ----------
    "LoginDTO": obj({"correo": {**S, "example": "luis@correo.unam.mx", "description": "Correo o usuario"},
                     "password": {**S, "format": "password"}}, ["correo", "password"]),
    "RegistroDTO": obj({
        "nombre": S, "correo": S,
        "password": {**S, "format": "password", "minLength": 8},
        "rol": {**S, "enum": ["consumidor", "vendedor", "repartidor"]},
        "documento": {**ARCHIVO, "description": "Comprobante de estudiante (pdf, png, jpg o jpeg)"},
    }, ["nombre", "correo", "password", "rol", "documento"]),
    "PerfilDTO": obj({"telefono": {**S, "nullable": True}, "facultad": S, "ubicacion_habitual": {**S, "nullable": True}}),
    "UsuarioDTO": obj({
        "id": I, "nombre": S, "correo": S,
        "rol": {**S, "enum": ["consumidor", "vendedor", "repartidor", "administrador"]},
        "estado": {**S, "enum": ["pendiente", "aprobado", "rechazado"]},
        "perfil": ref("PerfilDTO"),
    }, descripcion="Nunca incluye password_hash ni el documento de estudiante."),
    "SolicitudRolCrearDTO": obj({
        "rol": {**S, "enum": ["consumidor", "vendedor", "repartidor"]},
        "motivo": {**S, "minLength": 5, "maxLength": 500},
    }, ["rol", "motivo"]),
    "SolicitudRolDTO": obj({
        "id": I,
        "usuario": obj({"id": I, "nombre": S, "correo": S}),
        "rol_actual": S, "rol_solicitado": S, "motivo": S,
        "estado": {**S, "enum": ["pendiente", "aprobada", "rechazada"]},
        "creada_en": FECHA, "resuelta_en": {**FECHA, "nullable": True},
    }),
    "DecisionSolicitudDTO": obj({"estado": {**S, "enum": ["aprobada", "rechazada"]}}, ["estado"]),
    "DecisionCuentaDTO": obj({"estado": {**S, "enum": ["aprobado", "rechazado"]}}, ["estado"]),

    # ---------- SCM ----------
    "ResumenEstrellasDTO": obj({"promedio": {**N, "nullable": True}, "total": I}),
    "CrearProductoDTO": obj({
        "nombre": S, "descripcion": S,
        "precio": {**N, "minimum": 0}, "cantidad": {**I, "minimum": 0, "description": "Stock inicial"},
        "ubicacion_venta": S,
        "foto": {**ARCHIVO, "description": "png, jpg, jpeg o webp"},
    }, ["nombre", "descripcion", "precio", "cantidad", "ubicacion_venta", "foto"]),
    "ProductoDTO": obj({
        "id": I, "vendedor_id": I, "vendedor": S, "nombre": S, "descripcion": S,
        "foto": {**S, "example": "/api/media/fotos/ab12.png"},
        "precio": N, "ubicacion_venta": S, "stock": I,
        "calificacion": ref("ResumenEstrellasDTO"), "vendedor_calificacion": ref("ResumenEstrellasDTO"),
    }),
    "CarritoItemDTO": obj({"producto_id": I, "cantidad": {**I, "minimum": 1}}, ["producto_id", "cantidad"]),
    "CarritoDTO": obj({
        "items": lista(obj({"producto_id": I, "nombre": S, "precio": N, "cantidad": I, "foto": S})),
        "subtotal": N,
    }),

    # ---------- ERP ----------
    "CrearOrdenDTO": obj({
        "ubicacion_entrega": {**S, "example": "Biblioteca, entrada principal"},
        "metodo_pago": {**S, "enum": ["efectivo", "transferencia"], "default": "efectivo"},
    }, ["ubicacion_entrega"], "Los ítems se toman del carrito del comprador."),
    "FacturaDTO": obj({"folio": {**S, "example": "GOYA-000012"}, "metodo_pago": S,
                       "subtotal": N, "comision": N, "total": N, "emitida_en": FECHA}),
    "EvaluacionDTO": obj({"estrellas": {**I, "minimum": 1, "maximum": 5}, "comentario": S}),
    "ItemOrdenDTO": obj({
        "id": I, "producto_id": I, "vendedor_id": I, "producto": S, "foto": S, "vendedor": S,
        "cantidad": I, "precio_unitario": N, "evaluacion": {**ref("EvaluacionDTO"), "nullable": True},
    }),
    "OrdenDTO": obj({
        "id": I, "consumidor": S, "repartidor": {**S, "nullable": True}, "destino": S,
        "origenes": lista(S),
        "estado": {**S, "enum": ["creada", "preparando", "en_camino", "entregada", "cancelada"]},
        "creada_en": FECHA,
        "items": lista(ref("ItemOrdenDTO")),
        "factura": ref("FacturaDTO"),
        "vendedores": lista(obj({"id": I, "nombre": S})),
        "evaluaciones_vendedor": lista(obj({"vendedor_id": I, "vendedor": S, "estrellas": I, "comentario": S})),
        "clave_entrega": {**S, "example": "482913",
                          "description": "Solo la ve el comprador mientras el pedido está en curso."},
    }),
    "CambiarEstadoDTO": obj({
        "estado": {**S, "enum": ["preparando", "en_camino", "entregada", "cancelada"]},
        "clave": {**S, "description": "Clave de entrega del comprador; obligatoria al marcar 'entregada'."},
    }, ["estado"]),
    "EvaluarCompraDTO": obj({
        "productos": lista(obj({"item_id": I, "estrellas": {**I, "minimum": 1, "maximum": 5}, "comentario": S},
                               ["item_id", "estrellas"])),
        "vendedores": lista(obj({"vendedor_id": I, "estrellas": {**I, "minimum": 1, "maximum": 5}, "comentario": S},
                                ["vendedor_id", "estrellas"])),
    }),
}

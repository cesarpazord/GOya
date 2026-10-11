"""ERP · Permisos: qué estados puede fijar cada rol."""

PERMISOS = {
    "vendedor": {"preparando", "cancelada"},
    "consumidor": {"cancelada"},
    "repartidor": {"en_camino", "entregada"},
}


def puede_fijar(rol, estado):
    return estado in PERMISOS.get(rol, set())

"""ERP · Estados: máquina de estados de una orden."""

CREADA, PREPARANDO, EN_CAMINO, ENTREGADA, CANCELADA = (
    "creada", "preparando", "en_camino", "entregada", "cancelada")
ESTADOS = (CREADA, PREPARANDO, EN_CAMINO, ENTREGADA, CANCELADA)

TRANSICIONES = {
    CREADA: {PREPARANDO, CANCELADA},
    PREPARANDO: {EN_CAMINO, CANCELADA},
    EN_CAMINO: {ENTREGADA},
    ENTREGADA: set(),
    CANCELADA: set(),
}


class TransicionInvalida(ValueError):
    pass


def validar_transicion(actual, nuevo):
    if nuevo not in ESTADOS:
        raise TransicionInvalida(f"estado debe ser uno de {ESTADOS}")
    if nuevo not in TRANSICIONES[actual]:
        raise TransicionInvalida(f"transición inválida: {actual} → {nuevo}")
    return nuevo

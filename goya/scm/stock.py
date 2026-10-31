"""SCM · Stock: reglas puras de existencias."""


class StockInsuficiente(ValueError):
    pass


def reservar(disponible, cantidad):
    if cantidad < 1:
        raise ValueError("cantidad debe ser mayor a 0")
    if cantidad > disponible:
        raise StockInsuficiente(f"solo quedan {disponible} unidades")
    return disponible - cantidad


def reponer(disponible, cantidad):
    if cantidad < 1:
        raise ValueError("cantidad debe ser mayor a 0")
    return disponible + cantidad

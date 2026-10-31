"""SCM · Carrito: lógica pura del carrito de compras."""
from decimal import Decimal


class Carrito:
    def __init__(self):
        self._items = {}

    def agregar(self, producto_id, precio, cantidad, nombre=""):
        if cantidad < 1:
            raise ValueError("cantidad debe ser mayor a 0")
        previo = self._items.get(producto_id)
        total = cantidad + (previo["cantidad"] if previo else 0)
        self._items[producto_id] = {"producto_id": producto_id, "nombre": nombre,
                                    "precio": Decimal(str(precio)), "cantidad": total}

    def quitar(self, producto_id):
        self._items.pop(producto_id, None)

    def vaciar(self):
        self._items.clear()

    def items(self):
        return list(self._items.values())

    def esta_vacio(self):
        return not self._items

    def subtotal(self):
        return sum((i["precio"] * i["cantidad"] for i in self._items.values()), Decimal("0"))

import unittest
from decimal import Decimal
from goya.scm.carrito import Carrito
from goya.scm.stock import reservar, reponer, StockInsuficiente


class TestStock(unittest.TestCase):
    def test_reservar_y_reponer(self):
        self.assertEqual(reservar(5, 2), 3)
        self.assertEqual(reponer(3, 4), 7)

    def test_stock_insuficiente(self):
        with self.assertRaises(StockInsuficiente):
            reservar(1, 2)

    def test_cantidad_invalida(self):
        with self.assertRaises(ValueError):
            reservar(5, 0)


class TestCarrito(unittest.TestCase):
    def test_subtotal_y_acumulacion(self):
        c = Carrito()
        c.agregar(1, "40.00", 2, "Torta")
        c.agregar(1, "40.00", 1)
        c.agregar(2, "25.50", 1, "Café")
        self.assertEqual(c.subtotal(), Decimal("145.50"))
        self.assertEqual(len(c.items()), 2)

    def test_quitar_y_vaciar(self):
        c = Carrito()
        c.agregar(1, 10, 1)
        c.quitar(1)
        self.assertTrue(c.esta_vacio())
        c.agregar(2, 10, 1)
        c.vaciar()
        self.assertEqual(c.subtotal(), 0)

    def test_cantidad_invalida(self):
        with self.assertRaises(ValueError):
            Carrito().agregar(1, 10, 0)

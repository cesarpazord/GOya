import unittest
from decimal import Decimal
from goya.erp.estados import validar_transicion, TransicionInvalida
from goya.erp.total import calcular_total
from goya.erp.factura import formatear_folio


class TestEstados(unittest.TestCase):
    def test_flujo_valido(self):
        for a, b in [("creada", "preparando"), ("preparando", "en_camino"), ("en_camino", "entregada")]:
            self.assertEqual(validar_transicion(a, b), b)

    def test_invalidas(self):
        for a, b in [("creada", "entregada"), ("entregada", "cancelada"), ("en_camino", "cancelada")]:
            with self.assertRaises(TransicionInvalida):
                validar_transicion(a, b)

    def test_estado_desconocido(self):
        with self.assertRaises(TransicionInvalida):
            validar_transicion("creada", "volando")


class TestTotal(unittest.TestCase):
    def test_total_con_comision(self):
        t = calcular_total("80", 5)
        self.assertEqual((t["subtotal"], t["comision"], t["total"]),
                         (Decimal("80.00"), Decimal("4.00"), Decimal("84.00")))

    def test_redondeo(self):
        self.assertEqual(calcular_total("10.10", 5)["comision"], Decimal("0.51"))

    def test_negativo(self):
        with self.assertRaises(ValueError):
            calcular_total("-1", 5)


class TestFactura(unittest.TestCase):
    def test_folio(self):
        self.assertEqual(formatear_folio(12), "GOYA-000012")

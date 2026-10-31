import unittest
from goya.crm.seguridad import validar_rol, validar_estado_cuenta, ADMIN, ESTADOS_CUENTA


class TestCuentas(unittest.TestCase):
    def test_admin_no_es_rol_registrable(self):
        with self.assertRaises(ValueError):
            validar_rol(ADMIN)

    def test_estados(self):
        self.assertEqual(validar_estado_cuenta("aprobado"), "aprobado")
        self.assertEqual(validar_estado_cuenta("rechazado"), "rechazado")
        with self.assertRaises(ValueError):
            validar_estado_cuenta("pendiente")
        self.assertEqual(ESTADOS_CUENTA, ("pendiente", "aprobado", "rechazado"))


class TestSolicitudes(unittest.TestCase):
    def test_motivo(self):
        from goya.crm.seguridad import validar_motivo
        self.assertEqual(validar_motivo("  Quiero comprar  "), "Quiero comprar")
        for malo in ("", "  ab ", None, "x" * 501):
            with self.assertRaises(ValueError):
                validar_motivo(malo)

    def test_decision(self):
        from goya.crm.seguridad import validar_decision
        self.assertEqual(validar_decision("aprobada"), "aprobada")
        with self.assertRaises(ValueError):
            validar_decision("pendiente")

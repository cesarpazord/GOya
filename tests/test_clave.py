import unittest
from datetime import datetime, timedelta
from goya.erp.clave import generar_clave, clave_valida, bloqueada


class TestClave(unittest.TestCase):
    def test_generar(self):
        claves = {generar_clave() for _ in range(50)}
        self.assertTrue(all(len(c) == 6 and c.isdigit() for c in claves))
        self.assertGreater(len(claves), 1)

    def test_validar(self):
        self.assertTrue(clave_valida("482913", "482913"))
        self.assertTrue(clave_valida("482913", " 482 913 "))
        self.assertTrue(clave_valida("004829", 4829) is False)      # los ceros iniciales importan
        for malo in ("482914", "", None, True, "48291é", 3.5):
            self.assertFalse(clave_valida("482913", malo))

    def test_bloqueo(self):
        ahora = datetime(2026, 1, 1, 12, 0)
        self.assertFalse(bloqueada(None, ahora))
        self.assertTrue(bloqueada(ahora + timedelta(minutes=3), ahora))
        self.assertFalse(bloqueada(ahora - timedelta(seconds=1), ahora))

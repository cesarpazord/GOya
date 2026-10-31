import unittest
from goya.erp.evaluacion import validar_estrellas, validar_comentario, resumen_estrellas


class TestEvaluacion(unittest.TestCase):
    def test_estrellas(self):
        self.assertEqual(validar_estrellas(5), 5)
        self.assertEqual(validar_estrellas("3"), 3)
        for malo in (0, 6, -1, "x", None, True, 2.5 * 0 + 7):
            with self.assertRaises(ValueError):
                validar_estrellas(malo)

    def test_comentario(self):
        self.assertEqual(validar_comentario("  Muy rico  "), "Muy rico")
        self.assertEqual(validar_comentario(None), "")
        with self.assertRaises(ValueError):
            validar_comentario("x" * 301)

    def test_resumen(self):
        self.assertEqual(resumen_estrellas([]), {"promedio": None, "total": 0})
        self.assertEqual(resumen_estrellas([5, 4, 4]), {"promedio": 4.3, "total": 3})

import unittest
from goya.crm.seguridad import hash_password, verificar_password, validar_password, validar_rol


class TestSeguridad(unittest.TestCase):
    def test_hash_verifica(self):
        h = hash_password("secreta123")
        self.assertTrue(verificar_password("secreta123", h))
        self.assertFalse(verificar_password("otra", h))

    def test_hash_no_es_texto_plano_y_usa_sal(self):
        self.assertNotIn("secreta123", hash_password("secreta123"))
        self.assertNotEqual(hash_password("secreta123"), hash_password("secreta123"))

    def test_hash_corrupto(self):
        self.assertFalse(verificar_password("x", "basura"))

    def test_password_corta(self):
        with self.assertRaises(ValueError):
            validar_password("123")

    def test_rol(self):
        self.assertEqual(validar_rol("vendedor"), "vendedor")
        with self.assertRaises(ValueError):
            validar_rol("admin")

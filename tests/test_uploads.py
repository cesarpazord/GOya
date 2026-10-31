import unittest
from goya.uploads import extension_valida, EXT_FOTO, EXT_DOCUMENTO
from goya.erp.permisos import puede_fijar


class TestUploads(unittest.TestCase):
    def test_extensiones(self):
        self.assertTrue(extension_valida("foto.JPG", EXT_FOTO))
        self.assertFalse(extension_valida("foto.pdf", EXT_FOTO))
        self.assertTrue(extension_valida("credencial.pdf", EXT_DOCUMENTO))
        self.assertFalse(extension_valida("virus.exe", EXT_DOCUMENTO))
        self.assertFalse(extension_valida("sinextension", EXT_DOCUMENTO))


class TestPermisos(unittest.TestCase):
    def test_roles(self):
        self.assertTrue(puede_fijar("vendedor", "preparando"))
        self.assertFalse(puede_fijar("vendedor", "entregada"))
        self.assertTrue(puede_fijar("repartidor", "entregada"))
        self.assertFalse(puede_fijar("repartidor", "cancelada"))
        self.assertTrue(puede_fijar("consumidor", "cancelada"))
        self.assertFalse(puede_fijar("consumidor", "preparando"))

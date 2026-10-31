import unittest
from goya.observer import Observador, Sujeto


class Espia(Observador):
    def __init__(self):
        self.eventos = []

    def actualizar(self, orden, estado):
        self.eventos.append((orden, estado))


class TestObserver(unittest.TestCase):
    def test_notifica_a_todos(self):
        s, a, b = Sujeto(), Espia(), Espia()
        s.suscribir(a)
        s.suscribir(b)
        s.notificar("orden1", "creada")
        self.assertEqual(a.eventos, [("orden1", "creada")])
        self.assertEqual(b.eventos, [("orden1", "creada")])

    def test_no_duplica_suscripcion(self):
        s, a = Sujeto(), Espia()
        s.suscribir(a)
        s.suscribir(a)
        s.notificar("o", "creada")
        self.assertEqual(len(a.eventos), 1)

    def test_desuscribir(self):
        s, a = Sujeto(), Espia()
        s.suscribir(a)
        s.desuscribir(a)
        s.notificar("o", "creada")
        self.assertEqual(a.eventos, [])

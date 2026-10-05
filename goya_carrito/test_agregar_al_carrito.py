import threading
import unittest

from casos_uso import AgregarAlCarrito
from entidades import (
    CantidadInvalidaError,
    CompraPropiaError,
    Inventario,
    PerfilNoPermitidoError,
    Producto,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    Usuario,
    UsuarioNoEncontradoError,
    UsuarioNoVerificadoError,
)


def crear_caso(stock=5, reloj=None, ttl=900, extra_usuarios=()):
    usuarios = {
        "ana": Usuario("ana", True, {"consumidor"}),
        "beto": Usuario("beto", True, {"vendedor"}),
        "carla": Usuario("carla", True, {"consumidor", "vendedor"}),  # perfil dual
        "dani": Usuario("dani", False, {"consumidor"}),               # sin verificar
    }
    for u in extra_usuarios:
        usuarios[u.id] = u
    productos = {
        "P1": Producto("P1", "SKU-1", vendedor_id="beto", precio=30.0),
        "P2": Producto("P2", "SKU-2", vendedor_id="carla", precio=20.0),
    }
    inventarios = {"P1": Inventario("P1", stock), "P2": Inventario("P2", stock)}
    carritos = {}
    kwargs = {"ttl_segundos": ttl}
    if reloj:
        kwargs["reloj"] = reloj
    caso = AgregarAlCarrito(usuarios, productos, inventarios, carritos, **kwargs)
    return caso, inventarios, carritos


class TestReglasDeNegocio(unittest.TestCase):
    def test_agrega_producto_y_reserva_stock(self):
        caso, inv, _ = crear_caso()
        carrito = caso.ejecutar("P1", 2, "ana")
        self.assertEqual(carrito.items, {"P1": 2})
        self.assertEqual(inv["P1"].stock_reservado, 2)
        self.assertEqual(inv["P1"].disponible, 3)

    def test_rechaza_cantidad_invalida(self):
        caso, inv, _ = crear_caso()
        for cantidad in (0, -1):
            with self.assertRaises(CantidadInvalidaError):
                caso.ejecutar("P1", cantidad, "ana")
        self.assertEqual(inv["P1"].stock_reservado, 0)

    def test_rechaza_producto_o_usuario_inexistente(self):
        caso, _, _ = crear_caso()
        with self.assertRaises(ProductoNoEncontradoError):
            caso.ejecutar("NO-EXISTE", 1, "ana")
        with self.assertRaises(UsuarioNoEncontradoError):
            caso.ejecutar("P1", 1, "fantasma")

    def test_rechaza_pedir_mas_que_lo_disponible(self):
        caso, inv, _ = crear_caso()
        with self.assertRaises(StockInsuficienteError):
            caso.ejecutar("P1", 6, "ana")
        self.assertEqual(inv["P1"].stock_reservado, 0)

    # ---------- Reglas propias de Goya ----------
    def test_alumno_sin_credencial_verificada_no_compra(self):
        caso, inv, _ = crear_caso()
        with self.assertRaises(UsuarioNoVerificadoError):
            caso.ejecutar("P1", 1, "dani")
        self.assertEqual(inv["P1"].stock_reservado, 0)

    def test_usuario_sin_perfil_consumidor_no_compra(self):
        caso, _, _ = crear_caso()
        with self.assertRaises(PerfilNoPermitidoError):
            caso.ejecutar("P2", 1, "beto")  # beto solo es vendedor

    def test_perfil_dual_compra_a_otros_pero_no_a_si_mismo(self):
        caso, inv, _ = crear_caso()
        caso.ejecutar("P1", 1, "carla")  # producto de beto: permitido
        with self.assertRaises(CompraPropiaError):
            caso.ejecutar("P2", 1, "carla")  # su propio producto
        self.assertEqual(inv["P2"].stock_reservado, 0)

    def test_carrito_expirado_libera_su_stock(self):
        reloj = [0.0]
        caso, inv, _ = crear_caso(reloj=lambda: reloj[0], ttl=60)
        caso.ejecutar("P1", 3, "ana")
        self.assertEqual(inv["P1"].stock_reservado, 3)
        reloj[0] = 61.0  # pasó el TTL
        caso.ejecutar("P1", 1, "ana")  # carrito nuevo
        self.assertEqual(inv["P1"].stock_reservado, 1)


class TestConcurrencia(unittest.TestCase):
    """Dos o más alumnos quieren el mismo producto al mismo tiempo."""

    def _correr(self, hilos, stock):
        compradores = [Usuario(f"c{i}", True, {"consumidor"}) for i in range(hilos)]
        caso, inv, _ = crear_caso(stock=stock, extra_usuarios=compradores)
        barrera = threading.Barrier(hilos)  # todos arrancan al mismo tiempo
        resultados, candado = [], threading.Lock()

        def intentar(i):
            barrera.wait()
            try:
                caso.ejecutar("P1", 1, f"c{i}")
                r = "ok"
            except StockInsuficienteError:
                r = "sin_stock"
            with candado:
                resultados.append(r)

        lista = [threading.Thread(target=intentar, args=(i,)) for i in range(hilos)]
        for h in lista:
            h.start()
        for h in lista:
            h.join()
        return resultados, inv["P1"]

    def test_ultimo_producto_solo_lo_consigue_un_alumno(self):
        resultados, inventario = self._correr(hilos=20, stock=1)
        self.assertEqual(resultados.count("ok"), 1)
        self.assertEqual(resultados.count("sin_stock"), 19)
        self.assertEqual(inventario.stock_reservado, 1)

    def test_nunca_se_reserva_mas_de_lo_que_hay(self):
        resultados, inventario = self._correr(hilos=50, stock=5)
        self.assertEqual(resultados.count("ok"), 5)
        self.assertEqual(inventario.stock_reservado, 5)
        self.assertEqual(inventario.disponible, 0)


if __name__ == "__main__":
    unittest.main()

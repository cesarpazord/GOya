"""Caso de uso de Goya: AgregarAlCarrito(productoId, cantidad, usuarioId).

Lógica pura de negocio. Los "repositorios" son diccionarios en memoria;
en el sistema real serían adaptadores hacia la base de datos.
"""
import time
from threading import Lock

from entidades import (
    Carrito,
    CompraPropiaError,
    ProductoNoEncontradoError,
    UsuarioNoEncontradoError,
    validar_cantidad,
)


class AgregarAlCarrito:
    def __init__(self, usuarios, productos, inventarios, carritos,
                 ttl_segundos=900, reloj=time.monotonic):
        self._usuarios = usuarios        # usuario_id  -> Usuario
        self._productos = productos      # producto_id -> Producto
        self._inventarios = inventarios  # producto_id -> Inventario
        self._carritos = carritos        # usuario_id  -> Carrito
        self._ttl = ttl_segundos
        self._reloj = reloj
        self._lock = Lock()  # protege solo el diccionario de carritos

    def ejecutar(self, producto_id, cantidad, usuario_id):
        validar_cantidad(cantidad)

        usuario = self._usuarios.get(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError(usuario_id)
        usuario.puede_comprar()  # credencial verificada + perfil consumidor

        producto = self._productos.get(producto_id)
        if producto is None:
            raise ProductoNoEncontradoError(producto_id)
        if producto.vendedor_id == usuario_id:  # perfil dual: no comprarse a sí mismo
            raise CompraPropiaError(producto_id)

        carrito = self._obtener_carrito(usuario_id)
        self._inventarios[producto_id].reservar(cantidad)  # atómico
        carrito.agregar(producto_id, cantidad)
        return carrito

    def _obtener_carrito(self, usuario_id):
        with self._lock:
            carrito = self._carritos.get(usuario_id)
            if carrito is None or carrito.expirado():
                if carrito is not None:
                    self._liberar_reservas(carrito)
                carrito = Carrito(usuario_id, self._ttl, self._reloj)
                self._carritos[usuario_id] = carrito
            return carrito

    def _liberar_reservas(self, carrito):
        for producto_id, cantidad in carrito.items.items():
            self._inventarios[producto_id].liberar(cantidad)

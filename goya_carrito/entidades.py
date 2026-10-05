"""Capa de dominio pura de Goya: sin base de datos, sin frameworks."""
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock


# ---------- Errores de dominio ----------
class CantidadInvalidaError(ValueError):
    pass


class StockInsuficienteError(Exception):
    pass


class ProductoNoEncontradoError(KeyError):
    pass


class UsuarioNoEncontradoError(KeyError):
    pass


class UsuarioNoVerificadoError(Exception):
    """El alumno no ha validado su credencial."""


class PerfilNoPermitidoError(Exception):
    """El usuario no tiene perfil de consumidor."""


class CompraPropiaError(Exception):
    """Un vendedor no puede comprar su propio producto."""


def validar_cantidad(cantidad):
    if not isinstance(cantidad, int) or cantidad <= 0:
        raise CantidadInvalidaError("La cantidad debe ser un entero mayor a 0")


# ---------- Entidades ----------
@dataclass
class Usuario:
    """Alumno de CEU. Puede tener varios perfiles a la vez (perfil dual)."""
    id: str
    credencial_verificada: bool = False
    perfiles: set = field(default_factory=set)  # {"consumidor", "vendedor", "repartidor"}

    def puede_comprar(self):
        if not self.credencial_verificada:
            raise UsuarioNoVerificadoError(self.id)
        if "consumidor" not in self.perfiles:
            raise PerfilNoPermitidoError(self.id)


@dataclass(frozen=True)
class Producto:
    id: str
    sku: str
    vendedor_id: str
    precio: float


class Inventario:
    """Stock actual y reservado del producto de un vendedor.

    `reservar` es atómico: verificar y descontar ocurren dentro del mismo
    lock, así dos alumnos no pueden quedarse con la misma unidad.
    """

    def __init__(self, producto_id, stock_actual, stock_reservado=0):
        if stock_actual < 0 or stock_reservado < 0 or stock_reservado > stock_actual:
            raise ValueError("Stock inválido")
        self.producto_id = producto_id
        self.stock_actual = stock_actual
        self.stock_reservado = stock_reservado
        self._lock = Lock()

    @property
    def disponible(self):
        return self.stock_actual - self.stock_reservado

    def reservar(self, cantidad):
        validar_cantidad(cantidad)
        with self._lock:
            if cantidad > self.disponible:
                raise StockInsuficienteError(
                    f"Solo hay {self.disponible} disponible(s), pediste {cantidad}"
                )
            self.stock_reservado += cantidad

    def liberar(self, cantidad):
        validar_cantidad(cantidad)
        with self._lock:
            self.stock_reservado = max(0, self.stock_reservado - cantidad)


class Carrito:
    """Carrito del consumidor, con sesión y TTL (segundos)."""

    def __init__(self, usuario_id, ttl_segundos=900, reloj=time.monotonic):
        self.sesion = uuid.uuid4().hex
        self.usuario_id = usuario_id
        self.ttl = ttl_segundos
        self._reloj = reloj
        self._creado = reloj()
        self.items = {}  # producto_id -> cantidad

    def expirado(self):
        return self._reloj() - self._creado >= self.ttl

    def agregar(self, producto_id, cantidad):
        validar_cantidad(cantidad)
        self.items[producto_id] = self.items.get(producto_id, 0) + cantidad

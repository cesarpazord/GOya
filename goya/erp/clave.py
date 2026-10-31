"""ERP · Clave de entrega: código secreto que el comprador da al repartidor."""
import hmac
import secrets

LARGO = 6
MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 5


def generar_clave():
    return "".join(secrets.choice("0123456789") for _ in range(LARGO))


def clave_valida(esperada, ingresada):
    if isinstance(ingresada, bool) or not isinstance(ingresada, (str, int)):
        return False
    texto = str(ingresada).replace(" ", "").strip()
    return texto.isascii() and hmac.compare_digest(texto, esperada)


def bloqueada(hasta, ahora):
    return hasta is not None and hasta > ahora

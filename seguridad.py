"""CRM · Seguridad: hash de contraseñas (PBKDF2-SHA256) y validación de roles."""
import hashlib
import hmac
import os

ROLES = ("vendedor", "consumidor", "repartidor")
ITERACIONES = 200_000
MIN_PASSWORD = 8


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${salt.hex()}${dk.hex()}"


def verificar_password(password, almacenado):
    try:
        alg, iteraciones, salt, esperado = almacenado.split("$")
        if alg != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iteraciones))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), esperado)


def validar_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ValueError(f"la contraseña debe tener al menos {MIN_PASSWORD} caracteres")


def validar_rol(rol):
    if rol not in ROLES:
        raise ValueError(f"rol debe ser uno de {ROLES}")
    return rol

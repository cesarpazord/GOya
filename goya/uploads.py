"""Subida de archivos (fotos de producto y documentos de estudiante)."""
import os
import uuid

EXT_FOTO = {"png", "jpg", "jpeg", "webp"}
EXT_DOCUMENTO = {"pdf", "png", "jpg", "jpeg"}


def extension_valida(nombre, permitidas):
    return "." in nombre and nombre.rsplit(".", 1)[1].lower() in permitidas


def guardar(archivo, subcarpeta, permitidas, base):
    if archivo is None or not archivo.filename:
        raise ValueError("archivo requerido")
    if not extension_valida(archivo.filename, permitidas):
        raise ValueError("formato no permitido (usa " + ", ".join(sorted(permitidas)) + ")")
    nombre = f"{uuid.uuid4().hex}.{archivo.filename.rsplit('.', 1)[1].lower()}"
    carpeta = os.path.join(base, subcarpeta)
    os.makedirs(carpeta, exist_ok=True)
    archivo.save(os.path.join(carpeta, nombre))
    return nombre

"""Generación de la especificación OpenAPI 3 a partir de los endpoints anotados."""
from .esquemas import ESQUEMAS, ref

REGISTRO = []

DESCRIPCION = """API REST de **GO-ya**: compras y entregas entre estudiantes de la FI UNAM.

**Cómo probarla:** 1) ejecuta `POST /api/login` (por ejemplo con el usuario administrador).
2) El navegador guarda la cookie de sesión y *Try it out* la envía en cada petición.
Los endpoints con candado requieren sesión; algunos solo aplican a ciertos perfiles (comprador, vendedor, repartidor, administrador)."""


def documentar(metodo, ruta, resumen, tags, respuestas, body=None, body_tipo="application/json",
               parametros=(), descripcion="", sesion=True, registro=None):
    """Anota un endpoint: verbo, ruta exacta, DTO de entrada y respuestas (éxito y error)."""
    destino = REGISTRO if registro is None else registro

    def decorador(f):
        destino.append({"metodo": metodo.lower(), "ruta": ruta, "resumen": resumen, "tags": list(tags),
                        "respuestas": respuestas, "body": body, "body_tipo": body_tipo,
                        "parametros": list(parametros), "descripcion": descripcion, "sesion": sesion})
        return f
    return decorador


def ruta_id(nombre, descripcion):
    return {"name": nombre, "in": "path", "required": True, "description": descripcion,
            "schema": {"type": "integer"}}


def _contenido(nombre):
    if nombre.startswith("[]"):
        return {"application/json": {"schema": {"type": "array", "items": ref(nombre[2:])}}}
    return {"application/json": {"schema": ref(nombre)}}


def construir_spec(registro=None):
    entradas = REGISTRO if registro is None else registro
    paths = {}
    for e in entradas:
        op = {"summary": e["resumen"], "tags": e["tags"], "responses": {}}
        if e["descripcion"]:
            op["description"] = e["descripcion"]
        if e["parametros"]:
            op["parameters"] = e["parametros"]
        if e["body"]:
            op["requestBody"] = {"required": True, "content": {e["body_tipo"]: {"schema": ref(e["body"])}}}
        if e["sesion"]:
            op["security"] = [{"cookieAuth": []}]
        for codigo, (desc, esquema) in sorted(e["respuestas"].items()):
            r = {"description": desc}
            if esquema:
                r["content"] = _contenido(esquema)
            op["responses"][str(codigo)] = r
        paths.setdefault(e["ruta"], {})[e["metodo"]] = op
    etiquetas = sorted({t for e in entradas for t in e["tags"]})
    return {
        "openapi": "3.0.3",
        "info": {"title": "GO-ya API", "version": "1.0.0", "description": DESCRIPCION},
        "servers": [{"url": "/"}],
        "tags": [{"name": t} for t in etiquetas],
        "paths": paths,
        "components": {
            "schemas": ESQUEMAS,
            "securitySchemes": {"cookieAuth": {"type": "apiKey", "in": "cookie", "name": "session"}},
        },
    }

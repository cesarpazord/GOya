import json
import unittest

from goya.docs.esquemas import ESQUEMAS
from goya.docs.openapi import construir_spec, documentar, ruta_id


def refs(nodo):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k == "$ref":
                yield v.rsplit("/", 1)[-1]
            else:
                yield from refs(v)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from refs(v)


class TestOpenAPI(unittest.TestCase):
    def test_esquemas_se_resuelven_entre_si(self):
        self.assertFalse({r for r in refs(ESQUEMAS)} - set(ESQUEMAS))

    def test_dtos_no_exponen_secretos(self):
        campos = set(ESQUEMAS["UsuarioDTO"]["properties"])
        self.assertFalse(campos & {"password_hash", "documento_estudiante"})

    def test_decorador_arma_la_operacion(self):
        reg = []

        @documentar("PATCH", "/api/x/{oid}", "Demo", ["T"], body="CambiarEstadoDTO",
                    parametros=[ruta_id("oid", "ID")], registro=reg,
                    respuestas={200: ("ok", "OrdenDTO"), 400: ("mal", "ErrorDTO"), 204: ("sin cuerpo", None)})
        def f():
            return 1

        self.assertEqual(f(), 1)                       # el decorador no altera la función
        op = construir_spec(reg)["paths"]["/api/x/{oid}"]["patch"]
        self.assertEqual(op["requestBody"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/CambiarEstadoDTO")
        self.assertEqual(sorted(op["responses"]), ["200", "204", "400"])
        self.assertNotIn("content", op["responses"]["204"])
        self.assertEqual(op["security"], [{"cookieAuth": []}])
        self.assertEqual(op["parameters"][0]["in"], "path")

    def test_lista_y_multipart(self):
        reg = []
        documentar("POST", "/p", "r", ["T"], body="CrearProductoDTO", body_tipo="multipart/form-data",
                   sesion=False, registro=reg, respuestas={200: ("l", "[]ProductoDTO")})(lambda: 0)
        op = construir_spec(reg)["paths"]["/p"]["post"]
        self.assertIn("multipart/form-data", op["requestBody"]["content"])
        self.assertEqual(op["responses"]["200"]["content"]["application/json"]["schema"]["type"], "array")
        self.assertNotIn("security", op)

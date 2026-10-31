from flask import Blueprint, jsonify

from . import construir_spec

bp = Blueprint("docs", __name__)

PAGINA = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GO-ya API · Documentación</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  <style>body{margin:0}.topbar{display:none}</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: "/api-docs/openapi.json",
      dom_id: "#swagger-ui",
      tryItOutEnabled: true,
      persistAuthorization: true,
      docExpansion: "list",
      defaultModelsExpandDepth: 1,
    });
  </script>
</body>
</html>"""


@bp.get("/api-docs")
@bp.get("/docs")
def interfaz():
    return PAGINA


@bp.get("/api-docs/openapi.json")
def especificacion():
    return jsonify(construir_spec())

# GO-ya

Plataforma de negocios electrónicos y logística para la comunidad de la Facultad de Ingeniería (UNAM). Conecta vendedores, consumidores y repartidores dentro del campus.

```
                         GOya
                           │
       ┌───────────────────┼───────────────────┐
      CRM                 SCM                 ERP
   Usuario             Producto             Orden
   Perfil              Inventario           Estados
   Seguridad           Carrito              Total
   Hash                Stock                Factura
       └───────────────────┼───────────────────┘
                       Observer
                     Notificaciones
                    Pruebas unitarias
                     GitHub Actions
                      Pull Request
                         main
```

| Paquete | Archivos clave |
|---|---|
| `goya/crm` | `models.py` (Usuario, Perfil), `seguridad.py` (hash PBKDF2, roles), `routes.py` |
| `goya/scm` | `models.py` (Producto, Inventario, CarritoItem), `carrito.py`, `stock.py`, `routes.py` |
| `goya/erp` | `models.py` (Orden, ItemOrden, Factura), `estados.py`, `total.py`, `factura.py`, `routes.py` |
| `goya/observer` | `__init__.py` (Sujeto/Observador), `notificaciones.py` |
| `tests/` | pruebas unitarias por módulo |

## Ejecutar
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # opcional: borra DATABASE_URL para usar SQLite
docker compose up -d          # opcional: PostgreSQL
python run.py                 # http://127.0.0.1:5000
pytest
```

## Pantallas por rol
| Rol | Ve |
|---|---|
| Comprador | Productos (estilo marketplace, con calificaciones), Carrito, Mis compras con seguimiento y evaluación de producto y vendedor |
| Vendedor | Mis productos (título, descripción, foto, stock), Ventas, Avisos |
| Repartidor | Entregas (para recoger / mis entregas); para marcar una entrega debe ingresar la clave secreta del comprador |
| Administrador | Validación de estudiantes: ver el documento subido, aprobar o rechazar cuentas |

Registro con comprobante de estudiante (PDF/JPG/PNG); la cuenta queda pendiente hasta que el administrador la aprueba · inicio y cierre de sesión · cambio de perfil (comprador, vendedor, repartidor) mediante solicitud con motivo que aprueba el administrador · editar y eliminar productos.

Administrador inicial: usuario `administrador`, contraseña `administrador` (cámbialos con `ADMIN_USUARIO` y `ADMIN_PASSWORD` en `.env`).

## Documentación interactiva (OpenAPI / Swagger UI)
Con el servidor local en marcha: **http://127.0.0.1:5000/docs** (también `/api-docs`). La especificación está en `/api-docs/openapi.json`.
Los endpoints se anotan en el código con `@documentar(...)` (`goya/docs/openapi.py`) y los DTOs viven en `goya/docs/esquemas.py`.
Para probar: `POST /api/login` y luego *Try it out* en cualquier endpoint (la cookie de sesión se envía sola).

## Flujo de contribución
`rama feature` → Pruebas unitarias → Push → **GitHub Actions** (`.github/workflows/ci.yml`) → **Pull Request** (plantilla incluida) → merge a `main`.

## API
| Módulo | Ruta |
|---|---|
| Admin | `GET /api/admin/resumen` · `GET /api/admin/solicitudes?estado=` · `POST /api/admin/solicitudes/<id>/decision` · `GET /api/admin/usuarios?estado=` · `GET /api/admin/usuarios/<id>/documento` · `POST /api/admin/usuarios/<id>/estado` |
| CRM | `POST /api/registro` · `POST /api/login` · `POST /api/logout` · `GET /api/me` · `PUT /api/perfil` · `POST/GET /api/perfil/solicitud-rol` |
| SCM | `GET/POST /api/productos` · `PUT/DELETE /api/productos/<id>` · `POST /api/productos/<id>/reponer` · `GET/POST /api/carrito` · `DELETE /api/carrito/<pid>` |
| ERP | `GET/POST /api/ordenes` · `POST /api/ordenes/<id>/repartidor` · `PATCH /api/ordenes/<id>/estado` · `GET /api/ordenes/<id>/factura` · `POST /api/ordenes/<id>/evaluaciones` · `GET /api/productos/<id>/evaluaciones` |
| Observer | `GET /api/notificaciones` |

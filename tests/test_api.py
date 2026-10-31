import io
import tempfile
import unittest

try:
    import flask_sqlalchemy  # noqa: F401
    HAY_FLASK = True
except ImportError:
    HAY_FLASK = False


@unittest.skipUnless(HAY_FLASK, "Flask no instalado")
class TestFlujoCompleto(unittest.TestCase):
    def setUp(self):
        from goya import create_app
        self.app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TESTING": True,
                               "UPLOAD_FOLDER": tempfile.mkdtemp()})

    def admin(self):
        c = self.app.test_client()
        r = c.post("/api/login", json={"correo": "administrador", "password": "administrador"})
        self.assertEqual(r.status_code, 200)
        return c

    def nuevo(self, nombre, rol, aprobar=True):
        """Devuelve (cliente con sesión iniciada, usuario). Por defecto el admin aprueba la cuenta."""
        c = self.app.test_client()
        r = c.post("/api/registro", content_type="multipart/form-data", data={
            "nombre": nombre, "correo": f"{nombre}@x.mx", "password": "secreta123", "rol": rol,
            "documento": (io.BytesIO(b"%PDF-1.4"), "credencial.pdf")})
        self.assertEqual(r.status_code, 201, r.json)
        if aprobar:
            ok = self.admin().post(f"/api/admin/usuarios/{r.json['id']}/estado", json={"estado": "aprobado"})
            self.assertEqual(ok.status_code, 200)
        return c, r.json

    def producto(self, cliente, stock=5):
        return cliente.post("/api/productos", content_type="multipart/form-data", data={
            "nombre": "Torta", "descripcion": "De milanesa", "precio": "40", "cantidad": str(stock),
            "ubicacion_venta": "Edificio A", "foto": (io.BytesIO(b"\x89PNG"), "t.png")})

    def test_registro_exige_documento(self):
        r = self.app.test_client().post("/api/registro", content_type="multipart/form-data", data={
            "nombre": "x", "correo": "x@x.mx", "password": "secreta123", "rol": "consumidor"})
        self.assertEqual(r.status_code, 400)

    def test_login_logout(self):
        c, _ = self.nuevo("ana", "vendedor")
        self.assertEqual(c.get("/api/me").status_code, 200)
        c.post("/api/logout")
        self.assertEqual(c.get("/api/me").status_code, 401)
        ok = c.post("/api/login", json={"correo": "ana@x.mx", "password": "secreta123"})
        mal = c.post("/api/login", json={"correo": "ana@x.mx", "password": "incorrecta"})
        self.assertEqual((ok.status_code, mal.status_code), (200, 401))

    def test_permisos_por_rol(self):
        v, _ = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        self.assertEqual(self.producto(c).status_code, 403)
        self.assertEqual(c.get("/api/notificaciones").status_code, 200)
        self.assertEqual(self.app.test_client().get("/api/productos").status_code, 401)

    def test_producto_exige_foto_y_descripcion(self):
        v, _ = self.nuevo("ana", "vendedor")
        r = v.post("/api/productos", content_type="multipart/form-data", data={
            "nombre": "Torta", "descripcion": "x", "precio": "40", "cantidad": "5", "ubicacion_venta": "A"})
        self.assertEqual(r.status_code, 400)

    def test_orden_completa_y_vistas_por_rol(self):
        v, _ = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        r, _ = self.nuevo("eva", "repartidor")
        p = self.producto(v).json

        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 2})
        o = c.post("/api/ordenes", json={"ubicacion_entrega": "Biblioteca"}).json
        self.assertEqual(o["factura"]["total"], 84.0)
        self.assertEqual(c.get("/api/productos").json[0]["stock"], 3)
        self.assertEqual(r.get("/api/ordenes").json, [])          # aún no está lista

        est = lambda cli, e: cli.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": e})
        self.assertEqual(est(c, "preparando").status_code, 403)    # el comprador no prepara
        self.assertEqual(est(v, "preparando").status_code, 200)
        self.assertEqual(len(r.get("/api/ordenes").json), 1)       # ya la ve el repartidor
        self.assertEqual(est(r, "en_camino").status_code, 403)     # sin tomarla no puede
        self.assertEqual(r.post(f"/api/ordenes/{o['id']}/repartidor", json={}).status_code, 200)
        self.assertEqual(est(r, "en_camino").status_code, 200)
        clave = o["clave_entrega"]
        self.assertEqual(est(r, "entregada").status_code, 403)                  # sin clave no se entrega
        ok = r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "entregada", "clave": clave})
        self.assertEqual(ok.status_code, 200)

        n = lambda cli: len(cli.get("/api/notificaciones").json)
        self.assertEqual((n(c), n(v), n(r)), (4, 4, 2))

    def test_cancelar_repone_stock(self):
        v, _ = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        p = self.producto(v, stock=3).json
        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 3})
        o = c.post("/api/ordenes", json={"ubicacion_entrega": "Aula"}).json
        self.assertEqual(v.get("/api/productos").json[0]["stock"], 0)
        c.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "cancelada"})
        self.assertEqual(v.get("/api/productos").json[0]["stock"], 3)

    # ---------- administrador ----------
    def test_cuenta_pendiente_no_opera(self):
        c, u = self.nuevo("luis", "consumidor", aprobar=False)
        self.assertEqual(c.get("/api/me").json["estado"], "pendiente")
        self.assertEqual(c.get("/api/productos").status_code, 403)

    def test_admin_ve_documento_y_decide(self):
        c, u = self.nuevo("luis", "consumidor", aprobar=False)
        v, _ = self.nuevo("ana", "vendedor")
        adm = self.admin()
        pendientes = adm.get("/api/admin/usuarios?estado=pendiente").json
        self.assertEqual([x["correo"] for x in pendientes], ["luis@x.mx"])
        doc = adm.get(pendientes[0]["documento_url"])
        self.assertEqual((doc.status_code, doc.data), (200, b"%PDF-1.4"))
        self.assertEqual(v.get(pendientes[0]["documento_url"]).status_code, 403)   # otros roles no
        self.assertEqual(self.app.test_client().get(pendientes[0]["documento_url"]).status_code, 401)
        adm.post(f"/api/admin/usuarios/{u['id']}/estado", json={"estado": "rechazado"})
        self.assertEqual(c.get("/api/productos").status_code, 403)
        adm.post(f"/api/admin/usuarios/{u['id']}/estado", json={"estado": "aprobado"})
        self.assertEqual(c.get("/api/productos").status_code, 200)

    def test_no_se_puede_registrar_admin(self):
        r = self.app.test_client().post("/api/registro", content_type="multipart/form-data", data={
            "nombre": "x", "correo": "x@x.mx", "password": "secreta123", "rol": "administrador",
            "documento": (io.BytesIO(b"%PDF-1.4"), "c.pdf")})
        self.assertEqual(r.status_code, 400)

    # ---------- cambio de perfil por solicitud ----------
    def solicitar(self, cli, rol="consumidor", motivo="Ahora quiero comprar"):
        return cli.post("/api/perfil/solicitud-rol", json={"rol": rol, "motivo": motivo})

    def test_solicitud_cambio_de_perfil_aprobada(self):
        v, u = self.nuevo("ana", "vendedor")
        self.producto(v)
        adm = self.admin()
        self.assertEqual(adm.get("/api/admin/resumen").json["solicitudes_pendientes"], 0)

        r = self.solicitar(v)
        self.assertEqual((r.status_code, r.json["estado"]), (201, "pendiente"))
        self.assertEqual(v.get("/api/carrito").status_code, 403)          # sigue siendo vendedor
        self.assertEqual(self.solicitar(v).status_code, 409)              # una a la vez
        self.assertEqual(adm.get("/api/admin/resumen").json["solicitudes_pendientes"], 1)
        lista = adm.get("/api/admin/solicitudes?estado=pendiente").json
        self.assertEqual((lista[0]["usuario"]["correo"], lista[0]["motivo"]), ("ana@x.mx", "Ahora quiero comprar"))

        ok = adm.post(f"/api/admin/solicitudes/{r.json['id']}/decision", json={"estado": "aprobada"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(v.get("/api/me").json["rol"], "consumidor")
        self.assertEqual(v.get("/api/carrito").status_code, 200)
        self.assertEqual(v.get("/api/productos").json, [])                # sus publicaciones se retiran
        self.assertEqual(v.get("/api/perfil/solicitud-rol").json["estado"], "aprobada")
        self.assertEqual(adm.post(f"/api/admin/solicitudes/{r.json['id']}/decision",
                                  json={"estado": "rechazada"}).status_code, 409)   # ya resuelta

    def test_solicitud_rechazada_conserva_perfil(self):
        v, _ = self.nuevo("ana", "vendedor")
        adm = self.admin()
        sid = self.solicitar(v).json["id"]
        adm.post(f"/api/admin/solicitudes/{sid}/decision", json={"estado": "rechazada"})
        self.assertEqual(v.get("/api/me").json["rol"], "vendedor")
        self.assertEqual(self.solicitar(v, "repartidor", "Quiero repartir").status_code, 201)

    def test_solicitud_validaciones(self):
        v, _ = self.nuevo("ana", "vendedor")
        self.assertEqual(self.solicitar(v, motivo="").status_code, 400)
        self.assertEqual(self.solicitar(v, rol="vendedor").status_code, 400)
        self.assertEqual(self.solicitar(v, rol="administrador").status_code, 400)

    def test_solo_admin_decide_solicitudes(self):
        v, _ = self.nuevo("ana", "vendedor")
        sid = self.solicitar(v).json["id"]
        self.assertEqual(v.post(f"/api/admin/solicitudes/{sid}/decision", json={"estado": "aprobada"}).status_code, 403)
        self.assertEqual(v.get("/api/admin/solicitudes").status_code, 403)

    def test_solicitud_bloqueada_con_ordenes_en_curso(self):
        v, _ = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        p = self.producto(v).json
        sid = self.solicitar(v, "repartidor", "Quiero repartir").json["id"]      # sin órdenes: se acepta
        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 1})
        c.post("/api/ordenes", json={"ubicacion_entrega": "Aula"})
        self.assertEqual(self.solicitar(c, "vendedor", "Quiero vender").status_code, 409)
        r = self.admin().post(f"/api/admin/solicitudes/{sid}/decision", json={"estado": "aprobada"})
        self.assertEqual(r.status_code, 409)                                      # ahora tiene una venta en curso

    # ---------- editar y eliminar productos ----------
    def test_editar_producto(self):
        v, _ = self.nuevo("ana", "vendedor")
        otro, _ = self.nuevo("beto", "vendedor")
        p = self.producto(v).json
        datos = {"nombre": "Torta XL", "descripcion": "Más grande", "precio": "55", "cantidad": "9",
                 "ubicacion_venta": "Edificio B"}
        r = v.put(f"/api/productos/{p['id']}", content_type="multipart/form-data", data=datos)
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual((r.json["nombre"], r.json["precio"], r.json["stock"]), ("Torta XL", 55.0, 9))
        self.assertEqual(r.json["foto"], p["foto"])                 # sin foto nueva conserva la anterior
        r2 = v.put(f"/api/productos/{p['id']}", content_type="multipart/form-data",
                   data={**datos, "foto": (io.BytesIO(b"\x89PNG"), "nueva.png")})
        self.assertNotEqual(r2.json["foto"], p["foto"])
        self.assertEqual(otro.put(f"/api/productos/{p['id']}", content_type="multipart/form-data",
                                  data=datos).status_code, 403)

    def test_eliminar_producto(self):
        v, _ = self.nuevo("ana", "vendedor")
        otro, _ = self.nuevo("beto", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        p = self.producto(v).json
        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 1})
        self.assertEqual(otro.delete(f"/api/productos/{p['id']}").status_code, 403)
        self.assertEqual(v.delete(f"/api/productos/{p['id']}").status_code, 200)
        self.assertEqual(v.get("/api/productos").json, [])
        self.assertEqual(c.get("/api/productos").json, [])
        self.assertEqual(c.get("/api/carrito").json["items"], [])
        self.assertEqual(c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 1}).status_code, 404)

    # ---------- evaluaciones ----------
    def comprar_y_entregar(self, v, c, r, p, entregar=True):
        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 1})
        o = c.post("/api/ordenes", json={"ubicacion_entrega": "Aula"}).json
        if entregar:
            v.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "preparando"})
            r.post(f"/api/ordenes/{o['id']}/repartidor", json={})
            r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "en_camino"})
            r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "entregada", "clave": o["clave_entrega"]})
        return o

    def test_evaluar_producto_y_vendedor(self):
        v, vu = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        r, _ = self.nuevo("eva", "repartidor")
        p = self.producto(v).json
        o = self.comprar_y_entregar(v, c, r, p)
        cuerpo = {"productos": [{"item_id": o["items"][0]["id"], "estrellas": 5, "comentario": "Rica"}],
                  "vendedores": [{"vendedor_id": vu["id"], "estrellas": 4, "comentario": "Puntual"}]}
        res = c.post(f"/api/ordenes/{o['id']}/evaluaciones", json=cuerpo)
        self.assertEqual(res.status_code, 201, res.json)

        orden = c.get("/api/ordenes").json[0]
        self.assertEqual(orden["items"][0]["evaluacion"]["estrellas"], 5)
        self.assertEqual(orden["evaluaciones_vendedor"][0]["estrellas"], 4)
        prod = c.get("/api/productos").json[0]
        self.assertEqual(prod["calificacion"], {"promedio": 5.0, "total": 1})
        self.assertEqual(prod["vendedor_calificacion"], {"promedio": 4.0, "total": 1})
        ops = c.get(f"/api/productos/{p['id']}/evaluaciones").json["opiniones"]
        self.assertEqual((ops[0]["comentario"], ops[0]["consumidor"]), ("Rica", "luis"))
        self.assertEqual(c.post(f"/api/ordenes/{o['id']}/evaluaciones", json=cuerpo).status_code, 409)  # una sola vez

    def test_evaluar_exige_entrega_dueno_y_estrellas_validas(self):
        v, vu = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        otro, _ = self.nuevo("mara", "consumidor")
        r, _ = self.nuevo("eva", "repartidor")
        p = self.producto(v).json
        o = self.comprar_y_entregar(v, c, r, p, entregar=False)
        cuerpo = {"vendedores": [{"vendedor_id": vu["id"], "estrellas": 5}]}
        url = f"/api/ordenes/{o['id']}/evaluaciones"
        self.assertEqual(c.post(url, json=cuerpo).status_code, 409)       # aún no la recibe
        self.assertEqual(otro.post(url, json=cuerpo).status_code, 403)    # no es su compra
        self.assertEqual(v.post(url, json=cuerpo).status_code, 403)       # el vendedor no se autoevalúa
        v.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "preparando"})
        r.post(f"/api/ordenes/{o['id']}/repartidor", json={})
        r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "en_camino"})
        r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "entregada", "clave": o["clave_entrega"]})
        for malo in (0, 6, "x"):
            self.assertEqual(c.post(url, json={"vendedores": [{"vendedor_id": vu["id"], "estrellas": malo}]}).status_code, 400)
        self.assertEqual(c.post(url, json={}).status_code, 400)
        self.assertEqual(c.post(url, json=cuerpo).status_code, 201)

    # ---------- clave de entrega ----------
    def preparar_en_camino(self):
        v, _ = self.nuevo("ana", "vendedor")
        c, _ = self.nuevo("luis", "consumidor")
        r, _ = self.nuevo("eva", "repartidor")
        p = self.producto(v).json
        c.post("/api/carrito", json={"producto_id": p["id"], "cantidad": 1})
        o = c.post("/api/ordenes", json={"ubicacion_entrega": "Aula"}).json
        v.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "preparando"})
        r.post(f"/api/ordenes/{o['id']}/repartidor", json={})
        r.patch(f"/api/ordenes/{o['id']}/estado", json={"estado": "en_camino"})
        return v, c, r, o

    def test_clave_solo_la_ve_el_comprador(self):
        v, c, r, o = self.preparar_en_camino()
        self.assertRegex(o["clave_entrega"], r"^\d{6}$")
        self.assertEqual(c.get("/api/ordenes").json[0]["clave_entrega"], o["clave_entrega"])
        self.assertNotIn("clave_entrega", r.get("/api/ordenes").json[0])
        self.assertNotIn("clave_entrega", v.get("/api/ordenes").json[0])

    def test_entrega_con_clave(self):
        v, c, r, o = self.preparar_en_camino()
        url = f"/api/ordenes/{o['id']}/estado"
        mala = "000000" if o["clave_entrega"] != "000000" else "111111"
        self.assertEqual(r.patch(url, json={"estado": "entregada", "clave": mala}).status_code, 403)
        self.assertEqual(r.patch(url, json={"estado": "entregada"}).status_code, 403)
        self.assertEqual(c.get("/api/ordenes").json[0]["estado"], "en_camino")
        con_espacio = o["clave_entrega"][:3] + " " + o["clave_entrega"][3:]
        self.assertEqual(r.patch(url, json={"estado": "entregada", "clave": con_espacio}).status_code, 200)
        self.assertNotIn("clave_entrega", c.get("/api/ordenes").json[0])           # ya no se muestra

    def test_bloqueo_tras_intentos_fallidos(self):
        v, c, r, o = self.preparar_en_camino()
        url = f"/api/ordenes/{o['id']}/estado"
        mala = "000000" if o["clave_entrega"] != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(r.patch(url, json={"estado": "entregada", "clave": mala}).status_code, 403)
        correcta = r.patch(url, json={"estado": "entregada", "clave": o["clave_entrega"]})
        self.assertEqual(correcta.status_code, 429)                                 # bloqueada unos minutos

    # ---------- documentación ----------
    def test_swagger_ui_y_especificacion(self):
        c = self.app.test_client()
        for ruta in ("/docs", "/api-docs"):
            r = c.get(ruta)
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"SwaggerUIBundle", r.data)
        spec = c.get("/api-docs/openapi.json").json
        op = spec["paths"]["/api/ordenes"]["post"]
        self.assertEqual(op["requestBody"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/CrearOrdenDTO")
        self.assertTrue({"201", "400"} <= set(op["responses"]))
        self.assertIn("/api/ordenes/{oid}/estado", spec["paths"])
        faltan = set()
        def recorrer(n):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k == "$ref" and v.rsplit("/", 1)[-1] not in spec["components"]["schemas"]:
                        faltan.add(v)
                    else:
                        recorrer(v)
            elif isinstance(n, list):
                for v in n:
                    recorrer(v)
        recorrer(spec)
        self.assertEqual(faltan, set())

const $ = (s) => document.querySelector(s);
const money = (n) => "$" + Number(n).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const TABS = {
  consumidor: [["productos", "Productos"], ["carrito", "Carrito"], ["pedidos", "Mis compras"]],
  vendedor: [["vender", "Mis productos"], ["ventas", "Ventas"], ["avisos", "Avisos"]],
  repartidor: [["entregas", "Entregas"]],
  administrador: [["validaciones", "Cuentas"], ["solicitudes", "Solicitudes de perfil"]],
};
const PASOS = [["creada", "Pedido recibido"], ["preparando", "Preparando"], ["en_camino", "En camino"], ["entregada", "Entregado"]];

const state = { user: null, tab: null, productos: [], carrito: { items: [], subtotal: 0 }, ordenes: [], avisos: [], usuarios: [], solicitudes: [], resumen: { cuentas_pendientes: 0, solicitudes_pendientes: 0 }, solicitud: null, bannerCerrado: null, editando: null, filtroAdm: "pendiente", filtroSol: "pendiente" };

/* ---------- red ---------- */
async function api(url, method = "GET", body, silencioso = false) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) opts.body = body;
  else if (body) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
  const r = await fetch("/api" + url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && state.user) { state.user = null; mostrarAuth(); }
    if (!silencioso) toast(data.error || "Algo salió mal", true);
    throw new Error(data.error || r.status);
  }
  return data;
}

function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "show" + (err ? " err" : "");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (t.className = ""), 2800);
}

/* ---------- acceso ---------- */
function mostrarAuth() {
  $("#app").hidden = true;
  $("#auth").hidden = false;
}

function entrar(user) {
  state.user = user;
  $("#auth").hidden = true;
  $("#app").hidden = false;
  const aprobado = user.estado === "aprobado";
  const esAdmin = user.rol === "administrador";
  $("#user-nombre").textContent = user.nombre;
  $("#btn-rol").hidden = esAdmin || !aprobado;
  $("#user-rol").textContent = user.rol === "consumidor" ? "comprador" : user.rol;
  state.solicitud = null;
  state.resumen = { cuentas_pendientes: 0, solicitudes_pendientes: 0 };
  $("#buscar").hidden = user.rol !== "consumidor" || !aprobado;
  $("#buscar").value = "";
  resetFormProducto();
  state.tab = aprobado ? TABS[user.rol][0][0] : "pendiente";
  $("#nav").hidden = !aprobado || TABS[user.rol].length < 2;
  refrescar(true);
}

$("#t-login").onclick = () => cambiarAuth(true);
$("#t-registro").onclick = () => cambiarAuth(false);
function cambiarAuth(login) {
  $("#f-login").hidden = !login;
  $("#f-registro").hidden = login;
  $("#t-login").classList.toggle("on", login);
  $("#t-registro").classList.toggle("on", !login);
}

$("#f-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    entrar(await api("/login", "POST", Object.fromEntries(new FormData(e.target))));
    e.target.reset();
  } catch {}
});

$("#f-registro").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    entrar(await api("/registro", "POST", new FormData(e.target)));
    e.target.reset();
  } catch {}
});

$("#btn-salir").onclick = async () => {
  await api("/logout", "POST", null, true).catch(() => {});
  state.user = null;
  mostrarAuth();
};

/* ---------- datos ---------- */
async function refrescar(forzar = false) {
  const u = state.user;
  if (!u) return;
  if (!forzar && document.activeElement?.closest("form")) return;
  if (u.estado !== "aprobado") {
    try {
      const yo = await api("/me", "GET", null, true);
      if (yo.estado !== u.estado) return entrar(yo);
    } catch { return; }
    return pintar();
  }
  try {
    if (u.rol === "administrador") {
      const previas = state.resumen.solicitudes_pendientes;
      [state.usuarios, state.solicitudes, state.resumen] = await Promise.all([
        api("/admin/usuarios" + (state.filtroAdm ? "?estado=" + state.filtroAdm : ""), "GET", null, true),
        api("/admin/solicitudes" + (state.filtroSol ? "?estado=" + state.filtroSol : ""), "GET", null, true),
        api("/admin/resumen", "GET", null, true)]);
      if (state.resumen.solicitudes_pendientes > previas) toast("Hay solicitudes de cambio de perfil por revisar");
    } else if (u.rol === "consumidor") {
      [state.productos, state.carrito, state.ordenes] = await Promise.all([
        api("/productos", "GET", null, true), api("/carrito", "GET", null, true), api("/ordenes", "GET", null, true)]);
    } else if (u.rol === "vendedor") {
      [state.productos, state.ordenes, state.avisos] = await Promise.all([
        api("/productos", "GET", null, true), api("/ordenes", "GET", null, true), api("/notificaciones", "GET", null, true)]);
    } else {
      state.ordenes = await api("/ordenes", "GET", null, true);
    }
    if (u.rol !== "administrador") {
      const [yo, sol] = await Promise.all([api("/me", "GET", null, true), api("/perfil/solicitud-rol", "GET", null, true)]);
      state.solicitud = sol;
      if (yo.rol !== u.rol) {
        toast("Tu solicitud fue aprobada: ahora eres " + (yo.rol === "consumidor" ? "comprador" : yo.rol));
        return entrar(yo);
      }
    }
  } catch { return; }
  pintar();
}

/* ---------- navegación ---------- */
function pintarNav() {
  const u = state.user;
  $("#nav").innerHTML = TABS[u.rol].map(([id, nombre]) => {
    const extra = insignia(id);
    return `<button data-tab="${id}" class="${id === state.tab ? "on" : ""}">${nombre}${extra}</button>`;
  }).join("");
  document.querySelectorAll("main > section").forEach((s) => (s.hidden = s.id !== "v-" + state.tab));
}
$("#nav").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]");
  if (b) { state.tab = b.dataset.tab; pintar(); window.scrollTo(0, 0); }
});
$("#buscar").addEventListener("input", () => { state.tab = "productos"; pintar(); });

/* ---------- vistas ---------- */
function pintar() {
  pintarNav();
  const u = state.user;
  if (u.estado !== "aprobado") return pintarPendiente(u);
  pintarBanner(u);
  if (u.rol === "administrador") { pintarValidaciones(); pintarSolicitudes(); return; }
  if (u.rol === "consumidor") { pintarProductos(); pintarCarrito(); pintarPedidos(); }
  if (u.rol === "vendedor") { pintarMisProductos(); pintarVentas(); pintarAvisos(); }
  if (u.rol === "repartidor") pintarEntregas();
}

function tarjetaProducto(p, comprador) {
  return `<article class="prod">
    <img src="${esc(p.foto)}" alt="${esc(p.nombre)}" loading="lazy">
    <div class="cuerpo">
      <span class="precio">${money(p.precio)}</span>
      <h3>${esc(p.nombre)}</h3>
      <span class="desc">${esc(p.descripcion)}</span>
      <span class="meta">Vende ${esc(p.vendedor)} · ${esc(p.ubicacion_venta)}</span>
      <span class="meta">Producto ${cal(p.calificacion)} · Vendedor ${cal(p.vendedor_calificacion)}${comprador && p.calificacion.total ? ` · <button class="link-az" data-opiniones="${p.id}">Opiniones</button>` : ""}</span>
      <span class="${p.stock <= 3 ? "meta" : "verde"}">${p.stock <= 3 ? `¡Últimas ${p.stock}!` : `${p.stock} disponibles`}</span>
    </div>
    ${comprador ? `<form class="f-carrito" data-id="${p.id}">
        <input name="cantidad" type="number" min="1" max="${p.stock}" value="1" aria-label="Cantidad">
        <button class="btn chico" style="flex:1">Agregar al carrito</button></form>`
      : `<form class="reponer f-reponer" data-id="${p.id}">
        <input name="cantidad" type="number" min="1" value="1" aria-label="Unidades a reponer">
        <button class="btn sec chico">Reponer stock</button></form>
      <div class="reponer">
        <button class="btn sec chico" data-editar="${p.id}">Editar</button>
        <button class="btn peligro chico" data-eliminar="${p.id}">Eliminar</button></div>`}
  </article>`;
}

function pintarProductos() {
  const q = $("#buscar").value.trim().toLowerCase();
  const lista = state.productos.filter((p) => !q || (p.nombre + " " + p.descripcion).toLowerCase().includes(q));
  $("#grid-productos").innerHTML = lista.length ? lista.map((p) => tarjetaProducto(p, true)).join("")
    : `<div class="vacio" style="grid-column:1/-1">No encontramos publicaciones.</div>`;
}

function pintarCarrito() {
  const c = state.carrito;
  $("#carrito").innerHTML = !c.items.length
    ? `<h2>Carrito</h2><div class="vacio">Tu carrito está vacío.<br>¡Encuentra productos en tu facultad!</div>`
    : `<h2>Carrito</h2><div class="panel">
        ${c.items.map((i) => `<div class="fila">
          <img src="${esc(i.foto)}" alt="">
          <div class="info"><div>${esc(i.nombre)}</div><span class="meta">Cantidad: ${i.cantidad}</span></div>
          <div class="der"><div>${money(i.precio * i.cantidad)}</div>
            <button class="link" data-quitar="${i.producto_id}">Eliminar</button></div></div>`).join("")}
        <div class="total"><span>Subtotal</span><strong>${money(c.subtotal)}</strong></div>
        <small>La comisión de servicio se calcula al confirmar.</small>
      </div>
      <form id="f-orden" class="panel">
        <label>¿Dónde recibes tu pedido?<input name="ubicacion_entrega" placeholder="Ej. Biblioteca, entrada principal" required></label>
        <label>Medio de pago<select name="metodo_pago"><option value="efectivo">Efectivo al recibir</option><option value="transferencia">Transferencia</option></select></label>
        <button class="btn">Comprar ahora</button>
      </form>`;
}

function tracker(o) {
  if (o.estado === "cancelada") return `<div class="estado-txt cancelada">Pedido cancelado</div>`;
  const idx = PASOS.findIndex(([k]) => k === o.estado);
  const txt = { creada: "Esperando al vendedor", preparando: "El vendedor está preparando tu pedido", en_camino: "Tu pedido va en camino", entregada: "Entregado" }[o.estado];
  return `<div class="estado-txt ${o.estado}">${txt}</div>
    <div class="pasos">${PASOS.map(([, n], i) => `<div class="paso ${i <= idx ? "hecho" : ""}">${n}</div>`).join("")}</div>`;
}

function filaItems(o) {
  return o.items.map((i) => `<div class="fila"><img src="${esc(i.foto)}" alt="">
    <div class="info"><div>${esc(i.producto)}</div><span class="meta">${i.cantidad} × ${money(i.precio_unitario)} · ${esc(i.vendedor)}</span>
      ${i.evaluacion ? `<span class="meta">Calificación: <span class="rating">${estrellas(i.evaluacion.estrellas)}</span>${i.evaluacion.comentario ? " · " + esc(i.evaluacion.comentario) : ""}</span>` : ""}</div></div>`).join("");
}

const fecha = (iso) => new Date(iso + "Z").toLocaleDateString("es-MX", { day: "numeric", month: "short" });

function btnEstado(o, estado, texto, cls = "") {
  return `<button class="btn chico ${cls}" data-orden="${o.id}" data-estado="${estado}">${texto}</button>`;
}

function pintarPedidos() {
  $("#lista-pedidos").innerHTML = state.ordenes.length ? state.ordenes.map((o) => `
    <article class="orden">
      <header><span>${fecha(o.creada_en)} · ${o.factura.folio}</span><span>${money(o.factura.total)}</span></header>
      <div class="interior">
        ${tracker(o)}
        ${o.clave_entrega ? `<div class="clave"><span>Clave de entrega</span><strong>${o.clave_entrega.slice(0, 3)} ${o.clave_entrega.slice(3)}</strong><small>Dásela al repartidor solo cuando tengas tu pedido en la mano.</small></div>` : ""}
        <div class="meta">Entrega en ${esc(o.destino)}${o.repartidor ? ` · Repartidor: ${esc(o.repartidor)}` : ""}</div>
        ${filaItems(o)}
        ${o.evaluaciones_vendedor.map((e) => `<div class="meta">Vendedor ${esc(e.vendedor)}: <span class="rating">${estrellas(e.estrellas)}</span>${e.comentario ? " · " + esc(e.comentario) : ""}</div>`).join("")}
        ${evaluaPendiente(o) ? `<div class="acciones"><button class="btn chico" data-evaluar="${o.id}">Evaluar producto y vendedor</button></div>` : ""}
        <div class="meta">Subtotal ${money(o.factura.subtotal)} + comisión ${money(o.factura.comision)} · ${esc(o.factura.metodo_pago)}</div>
        ${["creada", "preparando"].includes(o.estado) ? `<div class="acciones">${btnEstado(o, "cancelada", "Cancelar compra", "peligro")}</div>` : ""}
      </div></article>`).join("") : `<div class="vacio">Todavía no has comprado nada.</div>`;
}

function pintarMisProductos() {
  $("#mis-productos").innerHTML = state.productos.length ? state.productos.map((p) => tarjetaProducto(p, false)).join("")
    : `<div class="vacio" style="grid-column:1/-1">Aún no has publicado productos.</div>`;
}

function pintarVentas() {
  $("#lista-ventas").innerHTML = state.ordenes.length ? state.ordenes.map((o) => `
    <article class="orden">
      <header><span>${fecha(o.creada_en)} · ${o.factura.folio} · Compra ${esc(o.consumidor)}</span><span>${money(o.factura.subtotal)}</span></header>
      <div class="interior">
        ${tracker(o)}
        <div class="meta">Entregar en ${esc(o.destino)}${o.repartidor ? ` · Repartidor: ${esc(o.repartidor)}` : " · Sin repartidor"}</div>
        ${filaItems(o)}
        ${o.evaluaciones_vendedor.filter((e) => e.vendedor_id === state.user.id).map((e) => `<div class="meta">Calificación como vendedor: <span class="rating">${estrellas(e.estrellas)}</span>${e.comentario ? " · " + esc(e.comentario) : ""}</div>`).join("")}
        <div class="acciones">
          ${o.estado === "creada" ? btnEstado(o, "preparando", "Preparar pedido") : ""}
          ${["creada", "preparando"].includes(o.estado) ? btnEstado(o, "cancelada", "Cancelar venta", "peligro") : ""}
        </div>
      </div></article>`).join("") : `<div class="vacio">Todavía no tienes ventas.</div>`;
}

function pintarAvisos() {
  $("#lista-avisos").innerHTML = state.avisos.length
    ? state.avisos.map((n) => `<li>${esc(n.mensaje)}<br><small>${new Date(n.creada_en + "Z").toLocaleString("es-MX")}</small></li>`).join("")
    : `<li>Sin avisos por ahora.</li>`;
}

function tarjetaEntrega(o, mia) {
  const u = state.user;
  return `<article class="orden">
    <header><span>${o.factura.folio}</span><span>${esc(o.estado.replace("_", " "))}</span></header>
    <div class="interior">
      <div class="estado-txt">${esc(o.origenes.join(" / "))} → ${esc(o.destino)}</div>
      <div class="meta">Para ${esc(o.consumidor)} · ${o.items.map((i) => `${esc(i.producto)} ×${i.cantidad}`).join(", ")}</div>
      <div class="acciones">
        ${!mia ? `<button class="btn chico" data-tomar="${o.id}">Tomar entrega</button>` : ""}
        ${mia && o.estado === "preparando" ? btnEstado(o, "en_camino", "Salí a entregar") : ""}
        ${mia && o.estado === "en_camino" ? `<button class="btn chico" data-entregar="${o.id}">Marcar como entregada</button>` : ""}
      </div></div></article>`;
}

function pintarEntregas() {
  const u = state.user;
  const disp = state.ordenes.filter((o) => !o.repartidor);
  const mias = state.ordenes.filter((o) => o.repartidor === u.nombre);
  $("#entregas-disp").innerHTML = disp.length ? disp.map((o) => tarjetaEntrega(o, false)).join("") : `<div class="vacio">No hay pedidos listos para recoger.</div>`;
  $("#entregas-mias").innerHTML = mias.length ? mias.map((o) => tarjetaEntrega(o, true)).join("") : `<div class="vacio">No tienes entregas asignadas.</div>`;
}

function resetFormProducto() {
  const f = $("#form-producto");
  state.editando = null;
  f.reset();
  f.foto.required = true;
  $("#preview").hidden = true;
  $("#titulo-form").textContent = "Publicar producto";
  $("#btn-guardar-producto").textContent = "Publicar";
  $("#btn-cancelar-edicion").hidden = true;
}

function editarProducto(id) {
  const p = state.productos.find((x) => x.id === id);
  if (!p) return;
  const f = $("#form-producto");
  state.editando = id;
  f.nombre.value = p.nombre;
  f.descripcion.value = p.descripcion;
  f.precio.value = p.precio;
  f.cantidad.value = p.stock;
  f.ubicacion_venta.value = p.ubicacion_venta;
  f.foto.value = "";
  f.foto.required = false;
  $("#preview").src = p.foto;
  $("#preview").hidden = false;
  $("#titulo-form").textContent = "Editar producto";
  $("#btn-guardar-producto").textContent = "Guardar cambios";
  $("#btn-cancelar-edicion").hidden = false;
  f.scrollIntoView({ behavior: "smooth", block: "center" });
}

const estrellas = (n) => "★".repeat(n) + "☆".repeat(5 - n);
const cal = (c) => (c && c.total ? `<span class="rating">★ ${c.promedio.toFixed(1)} <small>(${c.total})</small></span>` : `<small>sin calificar</small>`);
const evaluaPendiente = (o) => o.estado === "entregada" &&
  (o.items.some((i) => !i.evaluacion) || o.vendedores.some((v) => !o.evaluaciones_vendedor.some((e) => e.vendedor_id === v.id)));

const OPCIONES_ESTRELLAS = `<option value="">Sin calificar</option><option value="5">★★★★★ Excelente</option>
  <option value="4">★★★★☆ Muy bueno</option><option value="3">★★★☆☆ Regular</option>
  <option value="2">★★☆☆☆ Malo</option><option value="1">★☆☆☆☆ Muy malo</option>`;

function abrirEvaluacion(oid) {
  const o = state.ordenes.find((x) => x.id === oid);
  if (!o) return;
  $("#f-eval").dataset.orden = oid;
  const bloque = (titulo, nombre, clave) => `<fieldset class="eval"><legend>${titulo}: ${esc(nombre)}</legend>
    <select name="${clave}" aria-label="Calificación">${OPCIONES_ESTRELLAS}</select>
    <textarea name="c${clave}" rows="2" maxlength="300" placeholder="Comentario (opcional)"></textarea></fieldset>`;
  const prods = o.items.filter((i) => !i.evaluacion).map((i) => bloque("Producto", i.producto, "p-" + i.id));
  const vends = o.vendedores.filter((v) => !o.evaluaciones_vendedor.some((e) => e.vendedor_id === v.id))
    .map((v) => bloque("Vendedor", v.nombre, "v-" + v.id));
  $("#eval-campos").innerHTML = prods.concat(vends).join("");
  $("#dlg-eval").showModal();
}

async function verOpiniones(pid) {
  const d = await api(`/productos/${pid}/evaluaciones`);
  $("#opiniones-cont").innerHTML = `<h2 style="margin-top:0">${esc(d.producto)}</h2>
    <p>Producto ${cal(d.calificacion)} · Vendedor ${esc(d.vendedor)} ${cal(d.vendedor_calificacion)}</p>` +
    (d.opiniones.length ? d.opiniones.map((o) => `<div class="fila"><div class="info">
      <span class="rating">${estrellas(o.estrellas)}</span> <small>${esc(o.consumidor)} · ${fecha(o.fecha)}</small>
      ${o.comentario ? `<div>${esc(o.comentario)}</div>` : ""}</div></div>`).join("") : `<p class="meta">Aún no hay opiniones.</p>`);
  $("#dlg-opiniones").showModal();
}

const nombreRol = (r) => (r === "consumidor" ? "comprador" : r);

function insignia(id) {
  const n = id === "carrito" ? state.carrito.items.reduce((a, i) => a + i.cantidad, 0)
    : id === "validaciones" ? state.resumen.cuentas_pendientes
    : id === "solicitudes" ? state.resumen.solicitudes_pendientes : 0;
  return n ? `<span class="badge">${n}</span>` : "";
}

function pintarBanner(u) {
  const b = $("#banner-solicitud"), s = state.solicitud;
  const mostrar = u.rol !== "administrador" && s && (s.estado === "pendiente" || (s.estado === "rechazada" && state.bannerCerrado !== s.id));
  b.hidden = !mostrar;
  if (!mostrar) return;
  b.innerHTML = s.estado === "pendiente"
    ? `Tu solicitud para cambiar a <b>${nombreRol(s.rol_solicitado)}</b> está pendiente de aprobación del administrador.`
    : `El administrador rechazó tu solicitud para cambiar a <b>${nombreRol(s.rol_solicitado)}</b>. <button class="link" data-cerrar-banner="${s.id}">Cerrar</button>`;
}

function pintarSolicitudes() {
  $("#lista-solicitudes").innerHTML = state.solicitudes.length ? state.solicitudes.map((s) => `
    <article class="orden">
      <header><span>${esc(s.usuario.nombre)} · ${esc(s.usuario.correo)}</span><span class="estado-cuenta ${s.estado}">${s.estado}</span></header>
      <div class="interior">
        <div class="estado-txt" style="font-size:15px">${nombreRol(s.rol_actual)} → ${nombreRol(s.rol_solicitado)}</div>
        <div class="meta">Motivo: ${esc(s.motivo)}</div>
        <div class="meta">${fecha(s.creada_en)}</div>
        ${s.estado === "pendiente" ? `<div class="acciones">
          <button class="btn chico" data-decidir-sol="aprobada" data-sid="${s.id}">Aprobar</button>
          <button class="btn peligro chico" data-decidir-sol="rechazada" data-sid="${s.id}">Rechazar</button></div>` : ""}
      </div></article>`).join("") : `<div class="vacio">No hay solicitudes en este filtro.</div>`;
}

function pintarPendiente(u) {
  $("#msg-pendiente").innerHTML = u.estado === "rechazado"
    ? `<h2 style="margin-top:0">Tu cuenta fue rechazada</h2><p>No pudimos validar tu comprobante de estudiante. Crea una cuenta nueva con un documento vigente.</p>`
    : `<h2 style="margin-top:0">Estamos validando tu comprobante</h2><p>Un administrador revisará tu documento de estudiante. Podrás usar GO-ya en cuanto lo apruebe; esta pantalla se actualiza sola.</p>`;
}

function pintarValidaciones() {
  $("#lista-validaciones").innerHTML = state.usuarios.length ? state.usuarios.map((x) => `
    <article class="orden">
      <header><span>${esc(x.nombre)} · ${esc(x.correo)}</span><span class="estado-cuenta ${x.estado}">${x.estado}</span></header>
      <div class="interior">
        <div class="meta" style="margin-top:10px">Perfil solicitado: ${x.rol === "consumidor" ? "comprador" : esc(x.rol)}</div>
        <div class="acciones">
          <a class="btn sec chico" href="${esc(x.documento_url)}" target="_blank" rel="noopener">Ver documento</a>
          ${x.estado !== "aprobado" ? `<button class="btn chico" data-decidir="aprobado" data-uid="${x.id}">Aprobar</button>` : ""}
          ${x.estado !== "rechazado" ? `<button class="btn peligro chico" data-decidir="rechazado" data-uid="${x.id}">Rechazar</button>` : ""}
        </div>
      </div></article>`).join("") : `<div class="vacio">No hay cuentas en este filtro.</div>`;
}

/* ---------- eventos ---------- */
document.addEventListener("click", async (e) => {
  const t = e.target.closest("button");
  if (!t) return;
  try {
    if (t.dataset.estado) await api(`/ordenes/${t.dataset.orden}/estado`, "PATCH", { estado: t.dataset.estado });
    else if (t.dataset.tomar) await api(`/ordenes/${t.dataset.tomar}/repartidor`, "POST", {});
    else if (t.dataset.quitar) await api(`/carrito/${t.dataset.quitar}`, "DELETE");
    else if (t.dataset.editar) { editarProducto(+t.dataset.editar); return; }
    else if (t.dataset.eliminar) {
      if (!confirm("¿Eliminar este producto? Dejará de mostrarse en la tienda.")) return;
      await api(`/productos/${t.dataset.eliminar}`, "DELETE");
      if (state.editando === +t.dataset.eliminar) resetFormProducto();
      toast("Producto eliminado");
    } else if (t.dataset.decidir) {
      await api(`/admin/usuarios/${t.dataset.uid}/estado`, "POST", { estado: t.dataset.decidir });
      toast(t.dataset.decidir === "aprobado" ? "Cuenta aprobada" : "Cuenta rechazada");
    } else if (t.dataset.entregar) {
      $("#f-clave").dataset.orden = t.dataset.entregar;
      $("#f-clave").clave.value = "";
      $("#dlg-clave").showModal();
      return;
    } else if (t.dataset.evaluar) {
      abrirEvaluacion(+t.dataset.evaluar);
      return;
    } else if (t.dataset.opiniones) {
      await verOpiniones(+t.dataset.opiniones);
      return;
    } else if (t.dataset.decidirSol) {
      await api(`/admin/solicitudes/${t.dataset.sid}/decision`, "POST", { estado: t.dataset.decidirSol });
      toast(t.dataset.decidirSol === "aprobada" ? "Solicitud aprobada" : "Solicitud rechazada");
    } else if (t.dataset.cerrarBanner) {
      state.bannerCerrado = +t.dataset.cerrarBanner;
      pintar();
      return;
    } else return;
  } catch {}
  refrescar(true);
});

document.addEventListener("submit", async (e) => {
  const f = e.target;
  try {
    if (f.classList.contains("f-carrito")) {
      e.preventDefault();
      await api("/carrito", "POST", { producto_id: +f.dataset.id, cantidad: +f.cantidad.value });
      toast("Agregado al carrito");
    } else if (f.id === "f-orden") {
      e.preventDefault();
      await api("/ordenes", "POST", Object.fromEntries(new FormData(f)));
      toast("¡Compra realizada!");
      state.tab = "pedidos";
    } else if (f.classList.contains("f-reponer")) {
      e.preventDefault();
      await api(`/productos/${f.dataset.id}/reponer`, "POST", { cantidad: +f.cantidad.value });
      toast("Stock actualizado");
    } else if (f.id === "form-producto") {
      e.preventDefault();
      if (state.editando) {
        await api(`/productos/${state.editando}`, "PUT", new FormData(f));
        toast("Producto actualizado");
      } else {
        await api("/productos", "POST", new FormData(f));
        toast("Producto publicado");
      }
      resetFormProducto();
    } else return;
  } catch {}
  refrescar(true);
});

$("#btn-cancelar-edicion").onclick = resetFormProducto;
$("#filtro-adm").onchange = (e) => { state.filtroAdm = e.target.value; refrescar(true); };
$("#f-eval").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "ok") return;
  e.preventDefault();
  const f = e.target, fd = new FormData(f), productos = [], vendedores = [];
  for (const [k, v] of fd.entries()) {
    if (!v) continue;
    if (k.startsWith("p-")) productos.push({ item_id: +k.slice(2), estrellas: +v, comentario: fd.get("c" + k) || "" });
    if (k.startsWith("v-")) vendedores.push({ vendedor_id: +k.slice(2), estrellas: +v, comentario: fd.get("c" + k) || "" });
  }
  if (!productos.length && !vendedores.length) return toast("Elige al menos una calificación", true);
  try {
    await api(`/ordenes/${f.dataset.orden}/evaluaciones`, "POST", { productos, vendedores });
    $("#dlg-eval").close();
    toast("¡Gracias por tu opinión!");
    refrescar(true);
  } catch {}
});
$("#f-clave").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "ok") return;
  e.preventDefault();
  const f = e.target;
  try {
    await api(`/ordenes/${f.dataset.orden}/estado`, "PATCH", { estado: "entregada", clave: f.clave.value });
    $("#dlg-clave").close();
    toast("Entrega confirmada");
    refrescar(true);
  } catch {}
});
$("#filtro-sol").onchange = (e) => { state.filtroSol = e.target.value; refrescar(true); };
$("#btn-rol").onclick = () => {
  const u = state.user, pendiente = state.solicitud?.estado === "pendiente";
  const f = $("#f-rol");
  f.rol.innerHTML = [["consumidor", "Comprador"], ["vendedor", "Vendedor"], ["repartidor", "Repartidor"]]
    .filter(([k]) => k !== u.rol).map(([k, n]) => `<option value="${k}">${n}</option>`).join("");
  f.motivo.value = "";
  $("#estado-solicitud").textContent = pendiente ? "Ya tienes una solicitud pendiente de aprobación." : "El administrador debe aprobar el cambio. Seguirás con tu perfil actual mientras tanto.";
  f.querySelector("button[value=ok]").disabled = pendiente;
  $("#dlg-rol").showModal();
};
$("#f-rol").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "ok") return;
  e.preventDefault();
  try {
    state.solicitud = await api("/perfil/solicitud-rol", "POST", { rol: e.target.rol.value, motivo: e.target.motivo.value });
    $("#dlg-rol").close();
    toast("Solicitud enviada al administrador");
    pintar();
  } catch {}
});

$("#form-producto").foto.addEventListener("change", (e) => {
  const file = e.target.files[0];
  $("#preview").hidden = !file;
  if (file) $("#preview").src = URL.createObjectURL(file);
});

setInterval(() => { if (state.user && !document.hidden) refrescar(); }, 8000);

(async () => {
  try { entrar(await api("/me", "GET", null, true)); } catch { mostrarAuth(); }
})();

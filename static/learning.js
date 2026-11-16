(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ET = { vacia: "Vacía", con_cosas: "Con cosas" };
  let camaras = [], camId = null, notas = {}, ultimoEnt = null, sugerido = null, tGuardar = null;
  const urls = {};

  const api = async (url, o = {}) => {
    const r = await fetch(url, { credentials: "include", ...o });
    if (r.status === 401) { location.href = "/"; throw new Error("Sesión expirada"); }
    if (!r.ok) {
      let d = "";
      try { d = (await r.json()).detail; } catch (_) {}
      throw new Error(d || "Error " + r.status);
    }
    return r;
  };
  const j = async (u, o) => (await api(u, o)).json();
  const fd = (obj) => {
    const f = new FormData();
    for (const [k, v] of Object.entries(obj)) if (v != null && v !== "") f.append(k, v);
    return f;
  };
  const msg = (t, ok) => {
    const m = $("msg");
    m.textContent = t || "";
    m.style.color = ok ? "#2e7d32" : "#c62828";
  };

  // Muestra una imagen pedida con fetch (así se ve el error real si falla)
  async function imagen(el, url) {
    try {
      const b = await (await api(url + (url.includes("?") ? "&" : "?") + "t=" + Date.now())).blob();
      if (urls[el.id]) URL.revokeObjectURL(urls[el.id]);
      el.src = urls[el.id] = URL.createObjectURL(b);
      return true;
    } catch (e) {
      el.removeAttribute("src");
      return e.message;
    }
  }

  // ---------- Cámaras ----------
  async function cargarCamaras(verificar) {
    if (verificar) msg("Comprobando conexión de las cámaras...", true);
    try { camaras = await j("/learning/estado-camaras?verificar=" + (verificar ? 1 : 0)); }
    catch (e) { return msg(e.message); }
    if (verificar) msg("");
    $("camaras").innerHTML = camaras.length ? camaras.map((c) => {
      const est = c.online === true ? "🟢 en línea" : c.online === false ? "🔴 sin conexión" : "⚪ sin comprobar";
      return `<div class="l-cam ${c.id === camId ? "sel" : ""}" data-id="${c.id}">
        <strong>#${c.id} · ${esc(c.nombre)}</strong><br>
        <span class="l-ayuda">Empresa ${esc(c.empresa_id ?? "—")} · ${c.esta_activa ? "activa" : "inactiva"}</span><br>
        <span class="l-chip">${est}</span><span class="l-chip">${c.tiene_referencia ? "calibrada" : "sin foto vacía"}</span>
        <span class="l-chip">${c.ejemplos.vacia} vacías</span><span class="l-chip">${c.ejemplos.con_cosas} con cosas</span></div>`;
    }).join("") : '<p class="l-ayuda">No hay cámaras registradas.</p>';
  }

  async function seleccionar(id) {
    camId = id;
    $("notas").value = notas[id] || "";
    document.querySelectorAll(".l-cam").forEach((e) => e.classList.toggle("sel", +e.dataset.id === id));
    await Promise.all([frame(), referencia(), ejemplos()]);
    guardarPronto();
  }

  async function frame() {
    if (!camId) return;
    const r = await imagen($("img-actual"), `/learning/camaras/${camId}/frame`);
    msg(r === true ? "" : r);
  }
  async function referencia() {
    if (!camId) return;
    const r = await imagen($("img-ref"), `/learning/camaras/${camId}/referencia`);
    $("ref-estado").textContent = r === true ? "" : "(todavía no hay)";
  }

  // ---------- Ejemplos ----------
  async function ejemplos() {
    if (!camId) return;
    const d = await j(`/learning/ejemplos?camara_id=${camId}`);
    $("ej-conteo").textContent = `${d.vacia.length} fotos vacías · ${d.con_cosas.length} con cosas`;
    const todos = Object.entries(d).flatMap(([et, ns]) => ns.map((n) => [et, n]));
    $("galeria").innerHTML = todos.map(([et, n]) => `<figure class="l-ej" data-et="${et}" data-n="${esc(n)}">
      <img loading="lazy" alt="" src="/learning/ejemplos/${camId}/${et}/${encodeURIComponent(n)}">
      <figcaption>${ET[et]}</figcaption>
      <div class="l-fila"><button type="button" class="boton boton--sm" data-a="probar">Probar</button>
      ${et === "vacia" ? '<button type="button" class="boton boton--sm" data-a="ref">Usar como vacía</button>' : ""}
      <button type="button" class="boton boton--sm boton--peligro" data-a="borrar">Borrar</button></div></figure>`).join("")
      || '<p class="l-ayuda">Aún no hay ejemplos para esta cámara.</p>';
  }

  async function subir(files) {
    if (!camId || !files.length) return;
    const f = new FormData();
    f.append("camara_id", camId);
    f.append("etiqueta", $("ej-etiqueta").value);
    [...files].forEach((x) => f.append("archivos", x));
    try {
      const d = await j("/learning/ejemplos", { method: "POST", body: f });
      msg(`Fotos guardadas: ${d.guardadas}` + (d.invalidas ? ` · no válidas: ${d.invalidas}` : ""), !d.invalidas);
    } catch (e) { msg(e.message); }
    $("ej-archivos").value = "";
    await Promise.all([ejemplos(), cargarCamaras(false)]);
  }

  async function accionEjemplo(e) {
    const b = e.target.closest("button[data-a]");
    if (!b) return;
    const { et, n } = b.closest("figure").dataset;
    try {
      if (b.dataset.a === "borrar") {
        if (!confirm("¿Borrar este ejemplo?")) return;
        await j(`/learning/ejemplos/${camId}/${et}/${encodeURIComponent(n)}`, { method: "DELETE" });
        await Promise.all([ejemplos(), cargarCamaras(false)]);
      } else if (b.dataset.a === "ref") {
        if (!confirm("¿Usar esta foto como la habitación vacía de la cámara?")) return;
        await j(`/learning/ejemplos/${camId}/vacia/${encodeURIComponent(n)}/como-vacia`, { method: "POST" });
        msg("Foto vacía actualizada", true);
        await Promise.all([referencia(), cargarCamaras(false)]);
      } else {
        resultadoCargando();
        mostrar(await j(`/learning/camaras/${camId}/probar-foto`, { method: "POST", body: fd({ etiqueta: et, nombre: n, ...sliders() }) }));
      }
    } catch (err) { msg(err.message); }
  }

  // ---------- Prueba y sensibilidad ----------
  const sliders = () => ({ umbral_diff: $("umbral").value, area_min_pct: $("area").value });
  function setSliders(u, a) {
    $("umbral").value = u; $("area").value = a;
    $("umbral-val").textContent = (+u).toFixed(2); $("area-val").textContent = (+a).toFixed(1);
  }
  const resultadoCargando = () => { $("resultado").innerHTML = "<p>Analizando... la primera vez descarga el modelo y tarda.</p>"; };
  function mostrar(d) {
    $("resultado").innerHTML = `<p class="l-resultado-titulo">${d.hay_cosas ? "La habitación TIENE cosas" : "La habitación está vacía"}</p>
      <p>Cambió el ${esc(d.porcentaje)} % de la imagen (mínimo ${esc(d.area_min_pct)} %, umbral ${esc(d.umbral_diff)}).</p>
      <img class="l-img" alt="Zonas distintas en rojo" src="${esc(d.imagen)}">`;
  }
  async function probar(url, body) {
    if (!camId) return;
    resultadoCargando();
    try { mostrar(await j(url, { method: "POST", body })); }
    catch (e) { $("resultado").innerHTML = `<p style="color:#c62828">${esc(e.message)}</p>`; }
  }
  async function guardarConfig() {
    try {
      await j("/learning/config", { method: "PUT", body: fd(sliders()) });
      msg("Sensibilidad guardada: ahora la usa toda la aplicación", true);
      guardarPronto();
    } catch (e) { msg(e.message); }
  }

  // ---------- Entrenar ----------
  async function entrenar(modo) {
    const out = $("ent-resultado");
    $("btn-aplicar").hidden = true;
    out.innerHTML = "<p>Analizando los ejemplos... puede tardar varios minutos.</p>";
    try {
      const d = await j("/learning/entrenar", {
        method: "POST",
        body: fd({ modo, camara_id: $("ent-alcance").value === "camara" ? camId : "", ...sliders() }),
      });
      const m = d.matriz;
      out.innerHTML = `<p class="l-resultado-titulo">Acierto: ${d.precision} % (${d.total} fotos)</p>
        <p>Con umbral ${d.umbral_diff} y área mínima ${d.area_min_pct} %.</p>
        <table class="l-tabla"><tr><th></th><th>Dijo "hay cosas"</th><th>Dijo "vacía"</th></tr>
        <tr><th>Tenía cosas</th><td>${m.tp}</td><td>${m.fn}</td></tr>
        <tr><th>Estaba vacía</th><td>${m.fp}</td><td>${m.tn}</td></tr></table>
        ${d.tabla.length ? `<p style="margin-top:.75rem"><strong>Probados</strong></p><table class="l-tabla"><tr><th>Umbral</th><th>Mejor área</th><th>Acierto</th></tr>
          ${d.tabla.map((t) => `<tr><td>${t.umbral}</td><td>${t.area} %</td><td>${t.precision} %</td></tr>`).join("")}</table>` : ""}
        <p style="margin-top:.75rem"><strong>Detalle por foto</strong></p><div class="l-scroll"><table class="l-tabla">
        <tr><th>Cámara</th><th>Etiqueta</th><th>Cambió</th><th></th></tr>
        ${d.detalle.map((x) => `<tr><td>#${x.camara_id}</td><td>${ET[x.etiqueta]}</td><td>${x.porcentaje} %</td><td>${x.acierto ? "✔" : "✘ falló"}</td></tr>`).join("")}</table></div>`;
      ultimoEnt = { modo, precision: d.precision, total: d.total, umbral_diff: d.umbral_diff, area_min_pct: d.area_min_pct, fecha: new Date().toLocaleString() };
      if (modo === "buscar") { sugerido = d; $("btn-aplicar").hidden = false; }
      guardarPronto();
    } catch (e) { out.innerHTML = `<p style="color:#c62828">${esc(e.message)}</p>`; }
  }

  // ---------- Estado ----------
  const estado = () => ({ camara_id: camId, ...Object.fromEntries(Object.entries(sliders()).map(([k, v]) => [k, +v])), notas, ultimo_entrenamiento: ultimoEnt });
  const infoEstado = (g) => {
    const u = ultimoEnt ? ` · último entrenamiento: ${ultimoEnt.precision} % (${ultimoEnt.fecha})` : "";
    $("estado-info").textContent = g ? `✔ Estado guardado ${g}${u}` : "";
  };
  function guardarPronto() { clearTimeout(tGuardar); tGuardar = setTimeout(guardarEstado, 800); }
  async function guardarEstado() {
    try { infoEstado((await j("/learning/estado", { method: "PUT", body: fd({ datos: JSON.stringify(estado()) }) })).guardado); }
    catch (e) { $("estado-info").textContent = "No se pudo guardar: " + e.message; }
  }

  // ---------- Eventos ----------
  $("camaras").addEventListener("click", (e) => { const c = e.target.closest(".l-cam"); if (c) seleccionar(+c.dataset.id); });
  $("btn-escanear").addEventListener("click", () => cargarCamaras(true));
  $("btn-frame").addEventListener("click", frame);
  $("btn-vacia").addEventListener("click", async () => {
    if (!camId || !confirm("¿Guardar la imagen actual como habitación vacía? Reemplaza la anterior.")) return;
    try {
      await j(`/learning/camaras/${camId}/referencia`, { method: "POST" });
      msg("Foto vacía guardada", true);
      await Promise.all([referencia(), cargarCamaras(false)]);
    } catch (e) { msg(e.message); }
  });
  $("ej-archivos").addEventListener("change", (e) => subir(e.target.files));
  const zona = $("zona");
  ["dragover", "dragenter"].forEach((n) => zona.addEventListener(n, (e) => { e.preventDefault(); zona.classList.add("sobre"); }));
  ["dragleave", "drop"].forEach((n) => zona.addEventListener(n, () => zona.classList.remove("sobre")));
  zona.addEventListener("drop", (e) => { e.preventDefault(); subir(e.dataTransfer.files); });
  $("btn-capturar").addEventListener("click", async () => {
    if (!camId) return;
    msg("Capturando de la cámara...", true);
    try {
      const d = await j(`/learning/camaras/${camId}/ejemplos/capturar`, {
        method: "POST",
        body: fd({ etiqueta: $("ej-etiqueta").value, cantidad: $("cap-cant").value, pausa: $("cap-pausa").value }),
      });
      msg(`Fotos capturadas: ${d.guardadas}`, true);
      await Promise.all([ejemplos(), cargarCamaras(false)]);
    } catch (e) { msg(e.message); }
  });
  $("galeria").addEventListener("click", accionEjemplo);
  ["umbral", "area"].forEach((id) => $(id).addEventListener("input", () => { setSliders($("umbral").value, $("area").value); guardarPronto(); }));
  $("btn-probar").addEventListener("click", () => probar(`/learning/camaras/${camId}/probar`, fd(sliders())));
  $("prueba-archivo").addEventListener("change", (e) => {
    if (e.target.files[0]) probar(`/learning/camaras/${camId}/probar-foto`, fd({ archivo: e.target.files[0], ...sliders() }));
    e.target.value = "";
  });
  $("btn-guardar-config").addEventListener("click", guardarConfig);
  $("btn-evaluar").addEventListener("click", () => entrenar("evaluar"));
  $("btn-buscar").addEventListener("click", () => entrenar("buscar"));
  $("btn-aplicar").addEventListener("click", async () => {
    if (!sugerido) return;
    setSliders(sugerido.umbral_diff, sugerido.area_min_pct);
    await guardarConfig();
    $("btn-aplicar").hidden = true;
  });
  $("notas").addEventListener("input", () => { if (camId) { notas[camId] = $("notas").value; guardarPronto(); } });
  $("btn-guardar-estado").addEventListener("click", guardarEstado);
  $("logout-btn").addEventListener("click", async () => {
    try { await fetch("/auth/logout", { method: "POST", credentials: "include" }); } catch (_) {}
    location.href = "/";
  });

  // ---------- Inicio ----------
  (async () => {
    try {
      const yo = await j("/auth/yo");
      if (yo.rol !== "learning") { location.href = "/dashboard"; return; }
      $("learning-info").textContent = `${yo.nombre} · ${yo.email}`;
    } catch (_) { return; }
    try { const c = await j("/learning/config"); setSliders(c.umbral_diff, c.area_min_pct); } catch (_) { setSliders(0.15, 1.5); }
    let e = {};
    try { e = await j("/learning/estado"); } catch (_) {}
    notas = e.notas || {};
    ultimoEnt = e.ultimo_entrenamiento || null;
    if (e.umbral_diff && e.area_min_pct) setSliders(e.umbral_diff, e.area_min_pct);
    infoEstado(e.guardado);
    await cargarCamaras(false);
    const ids = camaras.map((c) => c.id);
    if (ids.length) await seleccionar(ids.includes(e.camara_id) ? e.camara_id : ids[0]);
    cargarCamaras(true); // comprueba en segundo plano cuáles responden
  })();
})();
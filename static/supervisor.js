// ============================================================
// Panel de supervisor (v1.6 — solo visualización)
// ============================================================

console.log("[supervisor.js] Cargado en:", window.location.href);

const logoutBtn         = document.getElementById("logout-btn");
const refrescarBtn      = document.getElementById("refrescar-btn");
const supervisorInfoEl  = document.getElementById("supervisor-info");

const deptoForm         = document.getElementById("crear-departamento-form");
const deptoNombreInput  = document.getElementById("depto-nombre");
const deptoMsg          = document.getElementById("depto-message");
const listaDeptosEl     = document.getElementById("lista-departamentos");

const camaraForm        = document.getElementById("crear-camara-form");
const camaraNombreInput = document.getElementById("camara-nombre");
const camaraUrlInput    = document.getElementById("camara-url");
const camaraDeptoSelect = document.getElementById("camara-depto");
const camaraMsg         = document.getElementById("camara-message");
const tablaCamarasEl    = document.getElementById("tabla-camaras");

// Referencias del modal
const modalEl       = document.getElementById("modal-camara");
const modalVideo    = document.getElementById("modal-video");
const modalImg      = document.getElementById("modal-img");
const modalTituloEl = document.getElementById("modal-titulo");
const modalUrlEl    = document.getElementById("modal-url");
const modalErrorEl  = document.getElementById("modal-error");
const modalCerrarEl = document.getElementById("modal-cerrar");

// Mapa departamento_id → nombre
const mapaDeptos = {};

// Cámara actualmente abierta en el modal
let camaraActualId = null;

// ------------------------------------------------------------
// Helpers
// ------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showMsg(el, texto, tipo = "error") {
  if (!el) return;
  el.textContent = texto;
  el.className = `mensaje ${tipo}`;
}

function setLoadingBtn(btn, cargando, textoBase) {
  if (!btn) return;
  btn.disabled = cargando;
  btn.classList.toggle("loading", cargando);
  const txt = btn.querySelector(".btn-text");
  if (txt) txt.textContent = cargando ? "Guardando..." : textoBase;
}

// ------------------------------------------------------------
// Cargar departamentos
// ------------------------------------------------------------
async function cargarDepartamentos() {
  if (!listaDeptosEl) return;
  listaDeptosEl.innerHTML = '<p class="tabla-vacia">Cargando departamentos...</p>';

  try {
    const res = await fetch("/supervisor/departamentos", { credentials: "include" });
    if (res.status === 401) { window.location.href = "/"; return; }
    if (!res.ok) {
      listaDeptosEl.innerHTML = '<p class="tabla-vacia">Error al cargar departamentos.</p>';
      return;
    }

    const data = await res.json();

    if (camaraDeptoSelect) {
      camaraDeptoSelect.innerHTML = '<option value="">— Selecciona un departamento —</option>';
    }
    Object.keys(mapaDeptos).forEach(k => delete mapaDeptos[k]);

    if (!data.length) {
      listaDeptosEl.innerHTML = '<p class="tabla-vacia">No hay departamentos. Crea el primero.</p>';
      return;
    }

    data.forEach(d => {
      mapaDeptos[d.id] = d.nombre;
      if (camaraDeptoSelect) {
        const opt = document.createElement("option");
        opt.value       = d.id;
        opt.textContent = d.nombre;
        camaraDeptoSelect.appendChild(opt);
      }
    });

    const filas = data.map(d => `
      <tr>
        <td>${d.id}</td>
        <td>${escapeHtml(d.nombre)}</td>
      </tr>`).join("");

    listaDeptosEl.innerHTML = `
      <table class="tabla">
        <thead>
          <tr><th>ID</th><th>Nombre</th></tr>
        </thead>
        <tbody>${filas}</tbody>
      </table>`;
  } catch (err) {
    listaDeptosEl.innerHTML = `<p class="tabla-vacia">Error: ${escapeHtml(err.message)}</p>`;
  }
}

// ------------------------------------------------------------
// Cargar cámaras (columna Acciones: ▶ Ver + 🗑 Borrar)
// ------------------------------------------------------------
async function cargarCamaras() {
  if (!tablaCamarasEl) return;
  tablaCamarasEl.innerHTML = '<p class="tabla-vacia">Cargando cámaras...</p>';

  try {
    const res = await fetch("/supervisor/camaras", { credentials: "include" });
    if (res.status === 401) { window.location.href = "/"; return; }
    if (!res.ok) {
      tablaCamarasEl.innerHTML = '<p class="tabla-vacia">Error al cargar cámaras.</p>';
      return;
    }

    const data = await res.json();

    if (!data.length) {
      tablaCamarasEl.innerHTML = '<p class="tabla-vacia">No hay cámaras. Crea la primera.</p>';
      return;
    }

    const filas = data.map(c => `
      <tr>
        <td>${c.id}</td>
        <td>${escapeHtml(c.nombre)}</td>
        <td><code class="url-stream">${escapeHtml(c.url_stream)}</code></td>
        <td>${escapeHtml(mapaDeptos[c.departamento_id] || "Depto. #" + c.departamento_id)}</td>
        <td>${c.esta_activa
          ? '<span class="badge badge--activo">Activa</span>'
          : '<span class="badge badge--inactivo">Inactiva</span>'}</td>
        <td class="tabla-acciones">
          <button class="boton boton--primario boton--sm"
                  data-accion="ver"
                  data-id="${c.id}"
                  data-nombre="${escapeHtml(c.nombre)}"
                  data-url="${escapeHtml(c.url_stream)}"
                  title="Ver cámara">
            ▶ Ver
          </button>
          <button class="boton boton--peligro boton--sm"
                  data-accion="borrar"
                  data-id="${c.id}"
                  data-nombre="${escapeHtml(c.nombre)}"
                  title="Borrar cámara">
            🗑 Borrar
          </button>
        </td>
      </tr>`).join("");

    tablaCamarasEl.innerHTML = `
      <table class="tabla">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>URL Stream</th>
            <th>Departamento</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>${filas}</tbody>
      </table>`;

    // Listener del botón ▶ Ver
    tablaCamarasEl.querySelectorAll('button[data-accion="ver"]').forEach(btn => {
      btn.addEventListener("click", () => {
        abrirModalCamara({
          id:     btn.dataset.id,
          nombre: btn.dataset.nombre,
          url:    btn.dataset.url,
        });
      });
    });

    // Listener del botón 🗑 Borrar
    tablaCamarasEl.querySelectorAll('button[data-accion="borrar"]').forEach(btn => {
      btn.addEventListener("click", async () => {
        const id     = btn.dataset.id;
        const nombre = btn.dataset.nombre;

        if (!confirm(`¿Borrar la cámara "${nombre}"? Esta acción no se puede deshacer.`)) {
          return;
        }

        btn.disabled = true;
        btn.textContent = "Borrando...";

        try {
          const r = await fetch(`/supervisor/camaras/${id}`, {
            method: "DELETE",
            credentials: "include",
          });
          const d = await r.json().catch(() => ({}));

          if (!r.ok) throw new Error(d.detail || "No se pudo borrar la cámara");

          await cargarCamaras();
        } catch (err) {
          alert("Error: " + err.message);
          btn.disabled = false;
          btn.textContent = "🗑 Borrar";
        }
      });
    });
  } catch (err) {
    tablaCamarasEl.innerHTML = `<p class="tabla-vacia">Error: ${escapeHtml(err.message)}</p>`;
  }
}

// ------------------------------------------------------------
// Modal de visualización de cámara
// ------------------------------------------------------------
let hlsInstance = null;

async function abrirModalCamara({ id, nombre, url }) {
  if (!modalEl || !modalVideo) {
    console.warn("[supervisor.js] Modal no encontrado en el DOM.");
    return;
  }

  camaraActualId = id;
  modalTituloEl.textContent = nombre || "Cámara";
  modalUrlEl.textContent    = url || "";
  modalErrorEl.textContent  = "";


  destruirHls();

  // Ocultar ambos por defecto
  modalVideo.style.display = "none";
  if (modalImg) modalImg.style.display = "none";

  const esHttp = /^https?:\/\//i.test(url || "");
  const esHls  = /\.m3u8(\?|$)/i.test(url || "");
  const esRtsp = /^rtsp:\/\//i.test(url || "");

  if (esRtsp) {
    modalErrorEl.textContent =
      "⚠️ Este navegador no puede reproducir RTSP directamente. " +
      "Usa una URL http:// con MJPEG (ej: http://IP:PUERTO/video).";
  } else if (!esHttp) {
    modalErrorEl.textContent = "⚠️ URL no válida.";
  } else if (esHls && window.Hls && Hls.isSupported()) {
    // ---- HLS ----
    modalVideo.style.display = "block";
    hlsInstance = new Hls({ lowLatencyMode: true });
    hlsInstance.loadSource(url);
    hlsInstance.attachMedia(modalVideo);
    hlsInstance.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) {
        modalErrorEl.textContent = "Error al reproducir el stream HLS.";
      }
    });
    modalVideo.play().catch(() => {});
  } else {
    // ---- Intentar como <video> normal (MP4, algunos MJPEG) ----
    modalVideo.style.display = "block";
    modalVideo.src = url;

    const ok = await new Promise((resolve) => {
      let resuelto = false;
      const marcar = (v) => { if (!resuelto) { resuelto = true; resolve(v); } };

      modalVideo.addEventListener("loadeddata", () => marcar(true), { once: true });
      modalVideo.addEventListener("error",     () => marcar(false), { once: true });

      modalVideo.play().catch(() => {});
      setTimeout(() => marcar(false), 2500);
    });

    if (!ok && modalImg) {
      // ---- Fallback a <img> para MJPEG ----
      modalVideo.pause();
      modalVideo.removeAttribute("src");
      modalVideo.load();
      modalVideo.style.display = "none";

      modalImg.style.display = "block";
      modalImg.src = url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();

      modalImg.onerror = () => {
        modalErrorEl.textContent =
          "No se pudo cargar el stream. Comprueba la URL y que la cámara esté encendida.";
      };
    } else if (!ok) {
      modalErrorEl.textContent =
        "No se pudo iniciar la reproducción. Verifica la URL.";
    }
  }

  modalEl.setAttribute("aria-hidden", "false");
}

function cerrarModalCamara() {
  if (!modalEl || !modalVideo) return;

  modalEl.setAttribute("aria-hidden", "true");
  destruirHls();

  modalVideo.pause();
  modalVideo.removeAttribute("src");
  modalVideo.load();

  if (modalImg) {
    modalImg.removeAttribute("src");
    modalImg.style.display = "none";
  }

  camaraActualId = null;
  modalErrorEl.textContent = "";
}

function destruirHls() {
  if (hlsInstance) {
    try { hlsInstance.destroy(); } catch { /* ignorar */ }
    hlsInstance = null;
  }
}

// ------------------------------------------------------------
// Listeners del modal
// ------------------------------------------------------------
if (modalCerrarEl) {
  modalCerrarEl.addEventListener("click", cerrarModalCamara);
}
if (modalEl) {
  modalEl.addEventListener("click", (e) => {
    if (e.target === modalEl) cerrarModalCamara();
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalEl && modalEl.getAttribute("aria-hidden") === "false") {
    cerrarModalCamara();
  }
});

// ------------------------------------------------------------
// Crear departamento
// ------------------------------------------------------------
if (deptoForm) {
  deptoForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showMsg(deptoMsg, "", "");

    const nombre = deptoNombreInput?.value.trim() || "";
    if (!nombre) { showMsg(deptoMsg, "El nombre es obligatorio"); return; }

    const btn = deptoForm.querySelector("button[type=submit]");
    setLoadingBtn(btn, true, "Crear departamento");

    try {
      const datos = new FormData();
      datos.append("nombre", nombre);

      const res  = await fetch("/supervisor/departamentos", {
        method: "POST", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo crear el departamento");

      showMsg(deptoMsg, `Departamento "${escapeHtml(data.departamento?.nombre)}" creado`, "success");
      deptoForm.reset();
      await cargarDepartamentos();
    } catch (err) {
      showMsg(deptoMsg, err.message);
    } finally {
      setLoadingBtn(btn, false, "Crear departamento");
    }
  });
}

// ------------------------------------------------------------
// Crear cámara
// ------------------------------------------------------------
if (camaraForm) {
  camaraForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showMsg(camaraMsg, "", "");

    const nombre       = camaraNombreInput?.value.trim() || "";
    const url_stream   = camaraUrlInput?.value.trim()    || "";
    const departamento = camaraDeptoSelect?.value        || "";

    if (!nombre || !url_stream) {
      showMsg(camaraMsg, "Nombre y URL son obligatorios");
      return;
    }
    if (!departamento) {
      showMsg(camaraMsg, "Selecciona un departamento");
      return;
    }

    const btn = camaraForm.querySelector("button[type=submit]");
    setLoadingBtn(btn, true, "Crear cámara");

    try {
      const datos = new FormData();
      datos.append("nombre",          nombre);
      datos.append("url_stream",      url_stream);
      datos.append("departamento_id", departamento);

      const res  = await fetch("/supervisor/camaras", {
        method: "POST", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo crear la cámara");

      showMsg(camaraMsg, `Cámara "${escapeHtml(data.camara?.nombre)}" creada`, "success");
      camaraForm.reset();
      await cargarCamaras();
    } catch (err) {
      showMsg(camaraMsg, err.message);
    } finally {
      setLoadingBtn(btn, false, "Crear cámara");
    }
  });
}

// ------------------------------------------------------------
// Eventos auxiliares
// ------------------------------------------------------------
if (refrescarBtn) {
  refrescarBtn.addEventListener("click", async () => {
    await cargarDepartamentos();
    await cargarCamaras();
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST", credentials: "include" });
    } catch { /* ignorar */ }
    localStorage.clear();
    window.location.href = "/";
  });
}

// ------------------------------------------------------------
// Carga inicial: verificar sesión + rol
// ------------------------------------------------------------
(async () => {
  console.log("[supervisor.js] Verificando sesión con /auth/yo...");
  try {
    const res  = await fetch("/auth/yo", { credentials: "include" });
    if (!res.ok) { window.location.href = "/"; return; }

    const data = await res.json();

    if (data.rol === "admin")   { window.location.href = "/admin";     return; }
    if (data.rol === "usuario") { window.location.href = "/dashboard"; return; }

    if (supervisorInfoEl) {
      const empresa = data.empresa_id != null ? ` · Empresa #${data.empresa_id}` : "";
      supervisorInfoEl.textContent = `${data.nombre || data.email}${empresa}`;
    }

    await cargarDepartamentos();
    await cargarCamaras();
  } catch (err) {
    console.error("[supervisor.js] Error en verificación inicial:", err);
    window.location.href = "/";
  }
})();
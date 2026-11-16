// ============================================================
// Panel de administración
// ============================================================

console.log("[admin.js] Cargado en:", window.location.href);

const form          = document.getElementById("crear-usuario-form");
const nombreInput   = document.getElementById("nombre");
const emailInput    = document.getElementById("email");
const passwordInput = document.getElementById("password");
const rolInput      = document.getElementById("rol");
const empresaSelect = document.getElementById("empresa_id");
const campoEmpresa  = document.getElementById("campo-empresa");
const submitBtn     = document.getElementById("submit-btn");
const messageEl     = document.getElementById("message");
const tablaEl       = document.getElementById("tabla-usuarios");
const refrescarBtn  = document.getElementById("refrescar-btn");
const logoutBtn     = document.getElementById("logout-btn");
const descargarAuditoriaBtn = document.getElementById("descargar-auditoria-btn");

const empresaForm   = document.getElementById("crear-empresa-form");
const empresaNombre = document.getElementById("empresa-nombre");
const empresaMsg    = document.getElementById("empresa-message");
const tablaEmpresasEl    = document.getElementById("tabla-empresas");
const refrescarEmpresasBtn = document.getElementById("refrescar-empresas-btn");

// ── Modal editar usuario
const modalUsuario      = document.getElementById("modal-usuario");
const editUsuarioId     = document.getElementById("edit-usuario-id");
const editNombre        = document.getElementById("edit-nombre");
const editRol           = document.getElementById("edit-rol");
const editEmpresaSelect = document.getElementById("edit-empresa_id");
const editCampoEmpresa  = document.getElementById("edit-campo-empresa");
const editEstaActivo    = document.getElementById("edit-esta-activo");
const editMessage       = document.getElementById("edit-message");
const editUsuarioForm   = document.getElementById("editar-usuario-form");
const cerrarModalUsuario = document.getElementById("cerrar-modal-usuario");

// ── Modal editar empresa
const modalEmpresa        = document.getElementById("modal-empresa");
const editEmpresaId       = document.getElementById("edit-empresa-id");
const editEmpresaNombre   = document.getElementById("edit-empresa-nombre");
const editEmpresaActiva   = document.getElementById("edit-empresa-activa");
const editEmpresaMessage  = document.getElementById("edit-empresa-message");
const editEmpresaForm     = document.getElementById("editar-empresa-form");
const cerrarModalEmpresa  = document.getElementById("cerrar-modal-empresa");

// ID del admin logueado (se llena al verificar sesión)
let adminId = null;

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

function showMessage(texto, tipo = "error") {
  if (!messageEl) return;
  messageEl.textContent = texto;
  messageEl.className = `mensaje ${tipo}`;
}

function showEmpresaMsg(texto, tipo = "error") {
  if (!empresaMsg) return;
  empresaMsg.textContent = texto;
  empresaMsg.className = `mensaje ${tipo}`;
}

function setLoading(cargando) {
  if (!submitBtn) return;
  submitBtn.disabled = cargando;
  submitBtn.classList.toggle("loading", cargando);
  const txt = submitBtn.querySelector(".btn-text");
  if (txt) txt.textContent = cargando ? "Creando..." : "Crear usuario";
}

function limpiarFormulario() {
  if (form) form.reset();
  if (nombreInput) nombreInput.focus();
  actualizarCampoEmpresa();
}

function badgeRol(rol) {
  const clases = {
    admin:      "badge badge--admin",
    supervisor: "badge badge--supervisor",
    usuario:    "badge badge--usuario",
    learning:   "badge badge--learning",
  };
  const etiquetas = { admin: "Admin", supervisor: "Supervisor", usuario: "Usuario", learning: "Learning" };
  const cls = clases[rol] || "badge";
  return `<span class="${cls}">${etiquetas[rol] || escapeHtml(rol)}</span>`;
}

// Mapa empresa_id → nombre (para mostrar en la tabla)
const mapaEmpresas = {};

// ------------------------------------------------------------
// Cargar empresas y llenar los selects
// ------------------------------------------------------------
async function cargarEmpresas() {
  try {
    const res = await fetch("/admin/empresas", { credentials: "include" });
    if (!res.ok) return;

    const empresas = await res.json();

    // Actualizar mapa
    empresas.forEach(e => { mapaEmpresas[e.id] = e.nombre; });

    // Llenar select de creación
    if (empresaSelect) {
      empresaSelect.innerHTML = '<option value="">— Selecciona una empresa —</option>';
      empresas.forEach(e => {
        const opt = document.createElement("option");
        opt.value       = e.id;
        opt.textContent = e.nombre + (e.esta_activa ? "" : " (inactiva)");
        empresaSelect.appendChild(opt);
      });
    }

    // Llenar select del modal de edición de usuario
    if (editEmpresaSelect) {
      editEmpresaSelect.innerHTML = '<option value="">— Selecciona una empresa —</option>';
      empresas.forEach(e => {
        const opt = document.createElement("option");
        opt.value       = e.id;
        opt.textContent = e.nombre + (e.esta_activa ? "" : " (inactiva)");
        editEmpresaSelect.appendChild(opt);
      });
    }

    // Renderizar tabla de empresas
    renderTablaEmpresas(empresas);
  } catch (err) {
    console.error("[admin.js] Error cargando empresas:", err);
  }
}

function renderTablaEmpresas(empresas) {
  if (!tablaEmpresasEl) return;

  if (!empresas.length) {
    tablaEmpresasEl.innerHTML = '<p class="tabla-vacia">No hay empresas registradas.</p>';
    return;
  }

  const filas = empresas.map(e => `
    <tr>
      <td>${e.id}</td>
      <td>${escapeHtml(e.nombre)}</td>
      <td>${e.esta_activa
        ? '<span class="badge badge--activo">Activa</span>'
        : '<span class="badge badge--inactivo">Inactiva</span>'}</td>
      <td>
        <div class="acciones-celda">
          <button class="boton boton--secundario boton--xs"
                  onclick="abrirEditarEmpresa(${e.id}, '${escapeHtml(e.nombre).replace(/'/g, "\\'")}', ${e.esta_activa})">
            ✏️ Editar
          </button>
          <button class="boton boton--peligro boton--xs"
                  onclick="eliminarEmpresa(${e.id}, '${escapeHtml(e.nombre).replace(/'/g, "\\'")}')">
            🗑️ Eliminar
          </button>
        </div>
      </td>
    </tr>`).join("");

  tablaEmpresasEl.innerHTML = `
    <table class="tabla">
      <thead>
        <tr>
          <th>ID</th>
          <th>Nombre</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>${filas}</tbody>
    </table>`;
}

// Mostrar/ocultar campo empresa según rol (formulario de creación)
function actualizarCampoEmpresa() {
  if (!rolInput || !campoEmpresa) return;
  const esAdmin = rolInput.value === "admin" || rolInput.value === "learning";
  campoEmpresa.style.display = esAdmin ? "none" : "";
  if (esAdmin && empresaSelect) empresaSelect.value = "";
}

if (rolInput) {
  rolInput.addEventListener("change", actualizarCampoEmpresa);
  actualizarCampoEmpresa();
}

// Mostrar/ocultar campo empresa en modal de edición
function actualizarEditCampoEmpresa() {
  if (!editRol || !editCampoEmpresa) return;
  const esAdmin = editRol.value === "admin" || editRol.value === "learning";
  editCampoEmpresa.style.display = esAdmin ? "none" : "";
  if (esAdmin && editEmpresaSelect) editEmpresaSelect.value = "";
}

if (editRol) {
  editRol.addEventListener("change", actualizarEditCampoEmpresa);
}

// ------------------------------------------------------------
// Cargar lista de usuarios
// ------------------------------------------------------------
async function cargarUsuarios() {
  if (!tablaEl) return;
  tablaEl.innerHTML = '<p class="tabla-vacia">Cargando usuarios...</p>';

  try {
    const res = await fetch("/admin/usuarios", { credentials: "include" });
    console.log("[admin.js] GET /admin/usuarios →", res.status);

    if (res.status === 401) { window.location.href = "/"; return; }
    if (res.status === 403) {
      alert("Sin permisos de administrador.");
      window.location.href = "/dashboard";
      return;
    }

    const data = await res.json();

    if (!data.length) {
      tablaEl.innerHTML = '<p class="tabla-vacia">No hay usuarios registrados.</p>';
      return;
    }

    const filas = data.map(u => `
      <tr>
        <td>
          ${escapeHtml(u.nombre) || '<em class="texto-muted">—</em>'}
          <span class="texto-muted">#${u.id}</span>
        </td>
        <td>${escapeHtml(u.email)}</td>
        <td>
          <div class="celda-rol-empresa">
            ${badgeRol(u.rol)}
            ${u.empresa_id != null
              ? `<span class="badge badge--empresa">${escapeHtml(mapaEmpresas[u.empresa_id] || "Empresa #" + u.empresa_id)}</span>`
              : '<em class="texto-muted">—</em>'}
          </div>
        </td>
        <td>${u.esta_activo
          ? '<span class="badge badge--activo">Activo</span>'
          : '<span class="badge badge--inactivo">Inactivo</span>'}</td>
        <td>
          <div class="acciones-celda">
            <button class="boton boton--secundario boton--xs"
                    onclick="abrirEditarUsuario(${u.id}, '${escapeHtml(u.nombre).replace(/'/g, "\\'")}', '${u.rol}', ${u.empresa_id ?? 'null'}, ${u.esta_activo})">
              ✏️ Editar
            </button>
            ${u.id !== adminId ? `
            <button class="boton boton--peligro boton--xs"
                    onclick="eliminarUsuario(${u.id}, '${escapeHtml(u.email).replace(/'/g, "\\'")}')">
              🗑️ Eliminar
            </button>` : '<em class="texto-muted">(tú)</em>'}
          </div>
        </td>
      </tr>`).join("");

    tablaEl.innerHTML = `
      <table class="tabla">
        <thead>
          <tr>
            <th>Nombre / ID</th>
            <th>Email</th>
            <th>Rol / Empresa</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>${filas}</tbody>
      </table>`;
  } catch (err) {
    console.error("[admin.js] Error cargando usuarios:", err);
    tablaEl.innerHTML = `<p class="tabla-vacia">Error: ${escapeHtml(err.message)}</p>`;
  }
}

// ------------------------------------------------------------
// Crear usuario
// ------------------------------------------------------------
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showMessage("", "");

    const nombre   = nombreInput?.value.trim()   || "";
    const email    = emailInput?.value.trim()     || "";
    const password = passwordInput?.value         || "";
    const rol      = rolInput?.value              || "usuario";
    const empresaId = (rol !== "admin" && rol !== "learning" && empresaSelect?.value)
      ? empresaSelect.value : "";

    if (!nombre || !email || !password) {
      showMessage("Completa todos los campos");
      return;
    }
    if (password.length < 6) {
      showMessage("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    if (rol !== "admin" && rol !== "learning" && !empresaId) {
      showMessage("Selecciona una empresa para este rol");
      return;
    }

    setLoading(true);

    try {
      const datos = new FormData();
      datos.append("nombre",     nombre);
      datos.append("email",      email);
      datos.append("password",   password);
      datos.append("rol",        rol);
      if (empresaId) datos.append("empresa_id", empresaId);

      const res  = await fetch("/admin/usuarios", {
        method: "POST", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo crear el usuario");

      showMessage(`Usuario "${escapeHtml(data.usuario?.nombre)}" creado correctamente`, "success");
      limpiarFormulario();
      cargarUsuarios();
    } catch (err) {
      showMessage(err.message);
    } finally {
      setLoading(false);
    }
  });
}

// ------------------------------------------------------------
// Crear empresa
// ------------------------------------------------------------
if (empresaForm) {
  empresaForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showEmpresaMsg("", "");

    const nombre = empresaNombre?.value.trim() || "";
    if (!nombre) { showEmpresaMsg("El nombre es obligatorio"); return; }

    const btn = empresaForm.querySelector("button[type=submit]");
    if (btn) { btn.disabled = true; btn.classList.add("loading"); }

    try {
      const datos = new FormData();
      datos.append("nombre", nombre);

      const res  = await fetch("/admin/empresas", {
        method: "POST", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo crear la empresa");

      showEmpresaMsg(`Empresa "${escapeHtml(data.empresa?.nombre)}" creada`, "success");
      empresaForm.reset();
      await cargarEmpresas();
    } catch (err) {
      showEmpresaMsg(err.message);
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
    }
  });
}

// ------------------------------------------------------------
// Modal: editar usuario
// ------------------------------------------------------------
function abrirEditarUsuario(id, nombre, rol, empresaId, estaActivo) {
  if (!modalUsuario) return;
  editUsuarioId.value     = id;
  editNombre.value        = nombre;
  editRol.value           = rol;
  editEstaActivo.checked  = estaActivo;
  editMessage.textContent = "";
  editMessage.className   = "mensaje";

  actualizarEditCampoEmpresa();
  if (empresaId && editEmpresaSelect) editEmpresaSelect.value = empresaId;

  modalUsuario.hidden = false;
  editNombre.focus();
}

function cerrarEditarUsuario() {
  if (modalUsuario) modalUsuario.hidden = true;
}

if (cerrarModalUsuario) cerrarModalUsuario.addEventListener("click", cerrarEditarUsuario);

if (editUsuarioForm) {
  editUsuarioForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id        = parseInt(editUsuarioId.value, 10);
    const nombre    = editNombre.value.trim();
    const rol       = editRol.value;
    const estaActivo = editEstaActivo.checked;
    const empresaId  = (rol !== "admin" && rol !== "learning" && editEmpresaSelect?.value)
      ? editEmpresaSelect.value : "";

    editMessage.textContent = "";
    editMessage.className   = "mensaje";

    if (!nombre) {
      editMessage.textContent = "El nombre es obligatorio";
      editMessage.className   = "mensaje error";
      return;
    }
    if (rol !== "admin" && rol !== "learning" && !empresaId) {
      editMessage.textContent = "Selecciona una empresa para este rol";
      editMessage.className   = "mensaje error";
      return;
    }

    const btn = editUsuarioForm.querySelector("button[type=submit]");
    if (btn) { btn.disabled = true; btn.classList.add("loading"); }

    try {
      const datos = new FormData();
      datos.append("nombre",      nombre);
      datos.append("rol",         rol);
      datos.append("esta_activo", estaActivo);
      if (empresaId) datos.append("empresa_id", empresaId);

      const res  = await fetch(`/admin/usuarios/${id}`, {
        method: "PUT", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo actualizar el usuario");

      cerrarEditarUsuario();
      await cargarUsuarios();
    } catch (err) {
      editMessage.textContent = err.message;
      editMessage.className   = "mensaje error";
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
    }
  });
}

// ------------------------------------------------------------
// Eliminar usuario
// ------------------------------------------------------------
async function eliminarUsuario(id, email) {
  if (!confirm(`¿Eliminar al usuario "${email}"? Esta acción no se puede deshacer.`)) return;

  try {
    const res  = await fetch(`/admin/usuarios/${id}`, {
      method: "DELETE", credentials: "include",
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) throw new Error(data.detail || "No se pudo eliminar el usuario");

    await cargarUsuarios();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// ------------------------------------------------------------
// Modal: editar empresa
// ------------------------------------------------------------
function abrirEditarEmpresa(id, nombre, estaActiva) {
  if (!modalEmpresa) return;
  editEmpresaId.value       = id;
  editEmpresaNombre.value   = nombre;
  editEmpresaActiva.checked = estaActiva;
  editEmpresaMessage.textContent = "";
  editEmpresaMessage.className   = "mensaje";

  modalEmpresa.hidden = false;
  editEmpresaNombre.focus();
}

function cerrarEditarEmpresa() {
  if (modalEmpresa) modalEmpresa.hidden = true;
}

if (cerrarModalEmpresa) cerrarModalEmpresa.addEventListener("click", cerrarEditarEmpresa);

if (editEmpresaForm) {
  editEmpresaForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id        = parseInt(editEmpresaId.value, 10);
    const nombre    = editEmpresaNombre.value.trim();
    const estaActiva = editEmpresaActiva.checked;

    editEmpresaMessage.textContent = "";
    editEmpresaMessage.className   = "mensaje";

    if (!nombre) {
      editEmpresaMessage.textContent = "El nombre es obligatorio";
      editEmpresaMessage.className   = "mensaje error";
      return;
    }

    const btn = editEmpresaForm.querySelector("button[type=submit]");
    if (btn) { btn.disabled = true; btn.classList.add("loading"); }

    try {
      const datos = new FormData();
      datos.append("nombre",      nombre);
      datos.append("esta_activa", estaActiva);

      const res  = await fetch(`/admin/empresas/${id}`, {
        method: "PUT", credentials: "include", body: datos,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) throw new Error(data.detail || "No se pudo actualizar la empresa");

      cerrarEditarEmpresa();
      await cargarEmpresas();
      await cargarUsuarios(); // refrescar tabla de usuarios (badge de empresa puede cambiar)
    } catch (err) {
      editEmpresaMessage.textContent = err.message;
      editEmpresaMessage.className   = "mensaje error";
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
    }
  });
}

// ------------------------------------------------------------
// Eliminar empresa
// ------------------------------------------------------------
async function eliminarEmpresa(id, nombre) {
  if (!confirm(`¿Eliminar la empresa "${nombre}"?\nFallará si tiene usuarios o cámaras asociadas.`)) return;

  try {
    const res  = await fetch(`/admin/empresas/${id}`, {
      method: "DELETE", credentials: "include",
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) throw new Error(data.detail || "No se pudo eliminar la empresa");

    await cargarEmpresas();
    await cargarUsuarios();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// ------------------------------------------------------------
// Eventos auxiliares
// ------------------------------------------------------------
if (refrescarBtn) refrescarBtn.addEventListener("click", cargarUsuarios);
if (refrescarEmpresasBtn) refrescarEmpresasBtn.addEventListener("click", cargarEmpresas);

if (descargarAuditoriaBtn) {
  descargarAuditoriaBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/admin/auditoria/descargar", { credentials: "include" });
      if (!res.ok) { alert("No se pudo generar el reporte."); return; }

      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = "reporte_auditoria.txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[admin.js] Error descargando auditoría:", err);
      alert("Error al descargar el reporte.");
    }
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

[nombreInput, emailInput, passwordInput].forEach(input => {
  if (!input) return;
  input.addEventListener("input", () => {
    input.classList.remove("invalid");
    if (messageEl?.classList.contains("error")) {
      messageEl.textContent = "";
      messageEl.className = "mensaje";
    }
  });
});

// Cerrar modales con Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    cerrarEditarUsuario();
    cerrarEditarEmpresa();
  }
});

// ------------------------------------------------------------
// Carga inicial: verificar sesión + rol
// ------------------------------------------------------------
(async () => {
  console.log("[admin.js] Verificando sesión con /auth/yo...");
  try {
    const res  = await fetch("/auth/yo", { credentials: "include" });
    if (!res.ok) { window.location.href = "/"; return; }

    const data = await res.json();
    if (data.rol !== "admin") {
      alert("No tienes permisos para acceder a esta página.");
      window.location.href = "/dashboard";
      return;
    }

    adminId = data.usuario_id; // guardar para ocultar botón de auto-eliminación

    await cargarEmpresas();
    await cargarUsuarios();
  } catch (err) {
    console.error("[admin.js] Error en verificación inicial:", err);
    window.location.href = "/";
  }
})();

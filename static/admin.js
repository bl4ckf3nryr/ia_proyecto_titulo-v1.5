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
  };
  const etiquetas = { admin: "Admin", supervisor: "Supervisor", usuario: "Usuario" };
  const cls = clases[rol] || "badge";
  return `<span class="${cls}">${etiquetas[rol] || escapeHtml(rol)}</span>`;
}

// Mapa empresa_id → nombre (para mostrar en la tabla)
const mapaEmpresas = {};

// ------------------------------------------------------------
// Cargar empresas y llenar el select
// ------------------------------------------------------------
async function cargarEmpresas() {
  try {
    const res = await fetch("/admin/empresas", { credentials: "include" });
    if (!res.ok) return;

    const empresas = await res.json();
    if (!empresaSelect) return;

    // Limpiar opciones excepto el placeholder
    empresaSelect.innerHTML = '<option value="">— Selecciona una empresa —</option>';

    empresas.forEach(e => {
      mapaEmpresas[e.id] = e.nombre;
      const opt = document.createElement("option");
      opt.value       = e.id;
      opt.textContent = e.nombre + (e.esta_activa ? "" : " (inactiva)");
      empresaSelect.appendChild(opt);
    });
  } catch (err) {
    console.error("[admin.js] Error cargando empresas:", err);
  }
}

// Mostrar/ocultar campo empresa según rol
function actualizarCampoEmpresa() {
  if (!rolInput || !campoEmpresa) return;
  const esAdmin = rolInput.value === "admin";
  campoEmpresa.style.display = esAdmin ? "none" : "";
  if (esAdmin && empresaSelect) empresaSelect.value = "";
}

if (rolInput) {
  rolInput.addEventListener("change", actualizarCampoEmpresa);
  actualizarCampoEmpresa(); // estado inicial
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
      </tr>`).join("");

    tablaEl.innerHTML = `
      <table class="tabla">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Email</th>
            <th>Rol</th>
            <th>Empresa</th>
            <th>Estado</th>
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
    const empresaId = (rol !== "admin" && empresaSelect?.value)
      ? empresaSelect.value : "";

    if (!nombre || !email || !password) {
      showMessage("Completa todos los campos");
      return;
    }
    if (password.length < 6) {
      showMessage("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    if (rol !== "admin" && !empresaId) {
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
      await cargarEmpresas();   // refrescar el select de empresas
    } catch (err) {
      showEmpresaMsg(err.message);
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
    }
  });
}

// ------------------------------------------------------------
// Eventos auxiliares
// ------------------------------------------------------------
if (refrescarBtn) refrescarBtn.addEventListener("click", cargarUsuarios);

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

    await cargarEmpresas();
    await cargarUsuarios();
  } catch (err) {
    console.error("[admin.js] Error en verificación inicial:", err);
    window.location.href = "/";
  }
})();

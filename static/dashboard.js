// ============================================================
// Dashboard — verifica sesión, muestra datos y cámaras activas
// ============================================================

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function cargarCamaras() {
  const tablaEl = document.getElementById("tabla-camaras");
  if (!tablaEl) return;

  tablaEl.innerHTML = '<p class="tabla-vacia">Cargando cámaras...</p>';

  try {
    const res = await fetch("/usuario/informes", { credentials: "include" });

    if (res.status === 401) { window.location.href = "/"; return; }
    if (!res.ok) {
      tablaEl.innerHTML = '<p class="tabla-vacia">No se pudieron cargar las cámaras.</p>';
      return;
    }

    const data = await res.json();
    const camaras = data.camaras || [];

    if (!camaras.length) {
      tablaEl.innerHTML = '<p class="tabla-vacia">No hay cámaras activas en tu empresa.</p>';
      return;
    }

    const filas = camaras.map(c => `
      <tr>
        <td>${escapeHtml(c.nombre)}</td>
        <td><code class="url-stream">${escapeHtml(c.url_stream)}</code></td>
        <td>${c.departamento_id != null ? "Depto. #" + c.departamento_id : '<em class="texto-muted">—</em>'}</td>
        <td><span class="badge badge--activo">Activa</span></td>
      </tr>`).join("");

    tablaEl.innerHTML = `
      <table class="tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>URL Stream</th>
            <th>Departamento</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>${filas}</tbody>
      </table>`;
  } catch (err) {
    const tablaEl2 = document.getElementById("tabla-camaras");
    if (tablaEl2) tablaEl2.innerHTML = `<p class="tabla-vacia">Error: ${escapeHtml(err.message)}</p>`;
  }
}

// --- Verificar sesión y mostrar UI ---
(async () => {
  try {
    const res = await fetch("/auth/yo", { credentials: "include" });
    if (!res.ok) { window.location.href = "/"; return; }

    const data = await res.json();

    // Redirigir si el rol no corresponde al dashboard
    if (data.rol === "admin")      { window.location.href = "/admin";      return; }
    if (data.rol === "supervisor") { window.location.href = "/supervisor"; return; }

    // Mostrar info del usuario
    const display = data.nombre ? `${data.nombre} (${data.email})` : data.email;
    const emailEl = document.getElementById("user-email");
    if (emailEl) emailEl.textContent = display;

    const empresaEl = document.getElementById("user-empresa");
    if (empresaEl && data.empresa_id != null) {
      empresaEl.textContent = "Empresa #" + data.empresa_id;
      empresaEl.style.display = "inline-block";
    }

    // Mostrar botón según rol (usuario normal → ninguno extra)
    const adminBtn      = document.getElementById("admin-btn");
    const supervisorBtn = document.getElementById("supervisor-btn");
    if (adminBtn)      adminBtn.hidden      = true;
    if (supervisorBtn) supervisorBtn.hidden = true;

    // Cargar cámaras
    await cargarCamaras();
  } catch {
    window.location.href = "/";
  }
})();

// --- Refrescar cámaras ---
const refrescarBtn = document.getElementById("refrescar-camaras-btn");
if (refrescarBtn) refrescarBtn.addEventListener("click", cargarCamaras);

// --- Logout ---
document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
  } catch { /* ignorar */ }
  localStorage.clear();
  window.location.href = "/";
});

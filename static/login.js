// ============================================================
// Login - envía POST a /auth/login y redirige según rol
// ============================================================

(function () {
  "use strict";

  const form        = document.getElementById("login-form");
  const emailInput  = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const submitBtn   = document.getElementById("submit-btn");
  const messageEl   = document.getElementById("message");

  if (!form || !emailInput || !passwordInput || !submitBtn || !messageEl) {
    console.error("[login.js] Faltan elementos en el HTML:", {
      form: !!form, email: !!emailInput, password: !!passwordInput,
      submitBtn: !!submitBtn, message: !!messageEl,
    });
    return;
  }

  // --- Si ya hay sesión, redirigir según rol ---
  (async () => {
    try {
      const res = await fetch("/auth/yo", { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        window.location.href = destinoPorRol(data.rol);
      }
    } catch { /* sin sesión */ }
  })();

  // --- Helpers ---
  function destinoPorRol(rol) {
    if (rol === "admin")      return "/admin";
    if (rol === "supervisor") return "/supervisor";
    return "/dashboard";
  }

  function showMessage(texto, tipo) {
    messageEl.textContent = texto;
    messageEl.className = "mensaje " + (tipo || "error");
  }

  function clearMessage() {
    messageEl.textContent = "";
    messageEl.className = "mensaje";
  }

  function setLoading(cargando) {
    submitBtn.disabled = cargando;
    submitBtn.classList.toggle("loading", cargando);
    const txt = submitBtn.querySelector(".btn-text");
    if (txt) txt.textContent = cargando ? "Verificando..." : "Entrar";
  }

  // --- Handler del submit ---
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    event.stopPropagation();
    clearMessage();

    const email    = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      emailInput.classList.toggle("invalid", !email);
      passwordInput.classList.toggle("invalid", !password);
      showMessage("Completa todos los campos");
      return false;
    }

    setLoading(true);

    try {
      const datos = new FormData();
      datos.append("email", email);
      datos.append("password", password);

      const res  = await fetch("/auth/login", {
        method: "POST",
        credentials: "include",
        body: datos,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "No se pudo iniciar sesión");
      }

      // Guardar datos no sensibles para UI
      localStorage.setItem("user_email",      data.email      || "");
      localStorage.setItem("user_nombre",     data.nombre     || "");
      localStorage.setItem("user_rol",        data.rol        || "usuario");
      localStorage.setItem("user_empresa_id", data.empresa_id != null ? String(data.empresa_id) : "");

      showMessage("¡Bienvenido, " + (data.nombre || data.email) + "!", "success");

      const destino = destinoPorRol(data.rol);
      setTimeout(function () {
        window.location.href = destino;
      }, 500);
    } catch (err) {
      showMessage(err.message || "Error de conexión");
      passwordInput.value = "";
      passwordInput.focus();
    } finally {
      setLoading(false);
    }

    return false;
  });

  // --- Limpiar estado de error al escribir ---
  [emailInput, passwordInput].forEach(function (input) {
    input.addEventListener("input", function () {
      input.classList.remove("invalid");
      clearMessage();
    });
  });
})();

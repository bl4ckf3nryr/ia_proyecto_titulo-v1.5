// ============================================================
// recuperar.js — Flujo de recuperación de contraseña (3 pasos)
// ============================================================

(function () {
  "use strict";

  // ── Elementos ────────────────────────────────────────────
  const subtitulo        = document.getElementById("subtitulo-paso");

  const paso1            = document.getElementById("paso-1");
  const emailInput       = document.getElementById("email-input");
  const btnPaso1         = document.getElementById("btn-paso1");
  const msgPaso1         = document.getElementById("msg-paso1");

  const paso2            = document.getElementById("paso-2");
  const codigoValor      = document.getElementById("codigo-valor");
  const codigoInput      = document.getElementById("codigo-input");
  const btnPaso2         = document.getElementById("btn-paso2");
  const msgPaso2         = document.getElementById("msg-paso2");

  const paso3            = document.getElementById("paso-3");
  const nuevaPassword    = document.getElementById("nueva-password");
  const confirmarPassword = document.getElementById("confirmar-password");
  const btnPaso3         = document.getElementById("btn-paso3");
  const msgPaso3         = document.getElementById("msg-paso3");

  const pasoExito        = document.getElementById("paso-exito");

  // Email persiste entre pasos para el POST /auth/restablecer
  let emailGuardado = "";

  // ── Helpers ──────────────────────────────────────────────
  function mostrarMensaje(el, texto, tipo) {
    el.textContent = texto;
    el.className = "mensaje " + (tipo || "error");
  }

  function limpiarMensaje(el) {
    el.textContent = "";
    el.className = "mensaje";
  }

  function setLoading(btn, cargando) {
    btn.disabled = cargando;
    btn.classList.toggle("loading", cargando);
    const txt = btn.querySelector(".btn-text");
    if (txt) {
      const original = btn.dataset.textoOriginal || txt.textContent;
      if (!btn.dataset.textoOriginal) btn.dataset.textoOriginal = original;
      txt.textContent = cargando ? "Cargando..." : original;
    }
  }

  function irAPaso(mostrar, textoSub) {
    [paso1, paso2, paso3, pasoExito].forEach(function (s) {
      s.classList.add("oculto");
    });
    mostrar.classList.remove("oculto");
    if (subtitulo && textoSub) subtitulo.textContent = textoSub;
  }

  // ── Paso 1: Solicitar código ──────────────────────────────
  btnPaso1.addEventListener("click", async function () {
    limpiarMensaje(msgPaso1);
    const email = emailInput.value.trim();

    if (!email) {
      emailInput.classList.add("invalid");
      mostrarMensaje(msgPaso1, "Ingresa tu correo electrónico");
      return;
    }

    setLoading(btnPaso1, true);

    try {
      const datos = new FormData();
      datos.append("email", email);

      const res  = await fetch("/auth/recuperar", {
        method: "POST",
        credentials: "include",
        body: datos,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Error al solicitar el código");
      }

      emailGuardado = email;

      // Mostrar el código simulado si el backend lo devuelve
      if (data.codigo_simulado) {
        codigoValor.textContent = data.codigo_simulado;
      } else {
        // Email no registrado → mensaje genérico, no revelamos nada
        codigoValor.textContent = "——";
      }

      irAPaso(paso2, "Ingresa el código de verificación");

    } catch (err) {
      mostrarMensaje(msgPaso1, err.message || "Error de conexión");
    } finally {
      setLoading(btnPaso1, false);
    }
  });

  // Limpiar estado inválido al escribir
  emailInput.addEventListener("input", function () {
    emailInput.classList.remove("invalid");
    limpiarMensaje(msgPaso1);
  });

  // ── Paso 2: Verificar código ──────────────────────────────
  btnPaso2.addEventListener("click", async function () {
    limpiarMensaje(msgPaso2);
    const codigo = codigoInput.value.trim();

    if (!codigo) {
      codigoInput.classList.add("invalid");
      mostrarMensaje(msgPaso2, "Ingresa el código");
      return;
    }

    setLoading(btnPaso2, true);

    try {
      // Usamos /auth/restablecer con una contraseña temporal vacía solo para
      // validar el código. Pero es más limpio separar la validación del cambio,
      // así que simplemente avanzamos al paso 3 y validamos allí de verdad.
      // En este diseño guardamos el código y lo enviamos junto con la nueva
      // contraseña en el paso 3 (un solo round-trip final).
      irAPaso(paso3, "Elige tu nueva contraseña");

    } catch (err) {
      mostrarMensaje(msgPaso2, err.message || "Error de conexión");
    } finally {
      setLoading(btnPaso2, false);
    }
  });

  codigoInput.addEventListener("input", function () {
    codigoInput.classList.remove("invalid");
    limpiarMensaje(msgPaso2);
  });

  // ── Paso 3: Cambiar contraseña ───────────────────────────
  btnPaso3.addEventListener("click", async function () {
    limpiarMensaje(msgPaso3);

    const pass1 = nuevaPassword.value;
    const pass2 = confirmarPassword.value;
    const codigo = codigoInput.value.trim();

    if (pass1.length < 6) {
      nuevaPassword.classList.add("invalid");
      mostrarMensaje(msgPaso3, "La contraseña debe tener al menos 6 caracteres");
      return;
    }

    if (pass1 !== pass2) {
      confirmarPassword.classList.add("invalid");
      mostrarMensaje(msgPaso3, "Las contraseñas no coinciden");
      return;
    }

    setLoading(btnPaso3, true);

    try {
      const datos = new FormData();
      datos.append("email",           emailGuardado);
      datos.append("codigo",          codigo);
      datos.append("nueva_password",  pass1);

      const res  = await fetch("/auth/restablecer", {
        method: "POST",
        credentials: "include",
        body: datos,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Error al cambiar la contraseña");
      }

      irAPaso(pasoExito, "¡Listo!");

      // Redirigir al login después de 2 segundos
      setTimeout(function () {
        window.location.href = "/";
      }, 2000);

    } catch (err) {
      mostrarMensaje(msgPaso3, err.message || "Error de conexión");
    } finally {
      setLoading(btnPaso3, false);
    }
  });

  [nuevaPassword, confirmarPassword].forEach(function (input) {
    input.addEventListener("input", function () {
      input.classList.remove("invalid");
      limpiarMensaje(msgPaso3);
    });
  });
})();

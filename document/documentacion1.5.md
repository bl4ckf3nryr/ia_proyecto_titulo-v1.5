# CHANGELOG — Gestor de Bultos

---

## Portada

**Proyecto:** Gestor de Bultos (TIHI84)  
**Versión:** 1.5.0  
**Fecha:** Noviembre 2026  
**Base:** v1.4.3 (con módulo de auditoría implementado)

---

## Resumen Ejecutivo

La versión 1.5 marca un hito importante en el desarrollo del sistema. Se completa el **CRUD completo** de las entidades centrales del panel de administración (usuarios y empresas), cerrando las operaciones de edición y eliminación que estaban pendientes desde versiones anteriores. Adicionalmente, el proyecto es **desplegado por primera vez en infraestructura cloud**: el backend corre en Render y la base de datos PostgreSQL está hospedada en Neon.tech, dejando atrás el entorno exclusivamente local.

---

## Nuevas Funcionalidades

### 1. Edición de Usuarios — `PUT /admin/usuarios/{id}`

Permite modificar los datos de un usuario existente desde el panel de administración.

**Campos editables:**
- Nombre de usuario
- Rol asignado
- Empresa asociada
- Estado activo/inactivo

**Restricción de seguridad:** No es posible cambiar el rol del administrador que tiene la sesión activa. Esto previene una escalada de privilegios accidental o intencionada.

---

### 2. Eliminación de Usuarios — `DELETE /admin/usuarios/{id}`

Permite eliminar permanentemente un usuario del sistema.

**Restricciones:**
- Un administrador no puede eliminarse a sí mismo mientras tenga la sesión activa.
- Cada eliminación queda registrada en el módulo de auditoría heredado de v1.4.3.

---

### 3. Edición de Empresas — `PUT /admin/empresas/{id}`

Permite actualizar la información de una empresa registrada.

**Campos editables:**
- Nombre de la empresa
- Estado activo/inactivo

---

### 4. Eliminación de Empresas — `DELETE /admin/empresas/{id}`

Permite eliminar una empresa del sistema.

**Restricción de integridad referencial:** No es posible eliminar una empresa si tiene **usuarios** o **cámaras** asociadas. El sistema retorna un error descriptivo en ese caso, protegiendo la consistencia de los datos.

---

### 5. Modales de Edición — Panel de Administración

Se incorporaron modales interactivos en el panel de administración para las operaciones de edición de usuarios y empresas.

**Características:**
- La edición se realiza sin recargar la página (comportamiento SPA).
- Los modales se pre-cargan con los datos actuales del registro seleccionado.
- El feedback de éxito o error se muestra en el mismo modal antes de cerrarse.

---

### 6. Despliegue en la Nube

El sistema fue desplegado exitosamente en infraestructura cloud por primera vez.

| Componente | Plataforma |
|---|---|
| Backend (FastAPI) | Render |
| Base de datos | Neon.tech (PostgreSQL) |

La configuración del despliegue está gestionada a través del archivo `render.yaml`.

---

## Archivos Modificados

| Archivo | Cambios |
|---|---|
| `base_de_datos/usuarios.py` | Se añadieron las funciones `actualizar_usuario` y `eliminar_usuario`. |
| `base_de_datos/empresas.py` | Se añadieron las funciones `actualizar_empresa` y `eliminar_empresa`. |
| `main.py` | Se registraron los endpoints `PUT` y `DELETE` para usuarios y empresas, incluyendo las validaciones de seguridad correspondientes. |
| `templates/admin.html` | Se incorporaron los modales de edición y la tabla de gestión de empresas. |
| `static/admin.js` | Se implementó la lógica JavaScript para edición, eliminación y renderizado dinámico de tablas. |
| `requirements.txt` | Se añadió la dependencia `psycopg2-binary` para la conexión con PostgreSQL. |
| `render.yaml` | Se creó/actualizó la configuración de despliegue para Python 3.11 y Playwright. |

---

## Notas de Migración

**No se requiere recrear la base de datos.**

La estructura de la base de datos existente en versiones anteriores (incluyendo `login.db`) es **compatible con v1.5**. No fue necesario borrar ni migrar el archivo de base de datos para el entorno local. Para el entorno cloud, la base de datos PostgreSQL en Neon.tech se inicializó directamente con el esquema actual.

---

## Pruebas Realizadas

El flujo de prueba end-to-end ejecutado para validar esta versión fue el siguiente:

1. **Crear usuario** → Se crea un nuevo usuario desde el panel de administración.
2. **Editar usuario (desactivar)** → Se edita el usuario recién creado y se marca como inactivo.
3. **Intentar login** → El usuario desactivado intenta iniciar sesión. El sistema rechaza el acceso correctamente.
4. **Eliminar usuario** → Se elimina el usuario desde el panel.
5. **Verificar auditoría** → Se confirma que el reporte de auditoría registra las acciones de edición y eliminación con la información correcta (actor, timestamp, acción).

---

*Documento generado para el proyecto de título TIHI84 — Ingeniería en Informática, INACAP.*

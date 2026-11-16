# 📦 Gestor de Bultos - Monitoreo Edge-to-Cloud

**Gestor de Bultos** es una solución integral de software diseñada para brindar visibilidad en tiempo real sobre el estado de ocupación física de los sectores de bodega en Centros de Distribución (CD).

El sistema integra visión por computador (Edge Computing) con un backend centralizado en la nube, permitiendo a supervisores y jefaturas tomar decisiones informadas sobre el uso del espacio sin depender de inspecciones manuales.

## 🚀 Características Principales

*   **Arquitectura Edge-to-Cloud:** Utiliza un Edge Device (NVIDIA Jetson Orin NX) con el modelo **YOLOv8** para procesar video localmente sin depender de la nube, enviando solo los datos relevantes al servidor.
*   **Sistema de Roles y Aislamiento:** Control de acceso basado en roles (`admin`, `supervisor`, `usuario`, `learning`). Cada supervisor y usuario solo visualiza la información de su propia empresa (Multi-tenant).
*   **CRUD Completo de Usuarios y Empresas:** Gestión integral con operaciones de crear, leer, actualizar y eliminar tanto usuarios como empresas, con auditoría integrada que registra automáticamente cada acción crítica.
*   **Visualización en Tiempo Real:** Dashboard web con integración de cámaras IP vía HLS, MJPEG y RTSP (procesado por el servidor).
*   **Módulo de Inteligencia Artificial (Learning):** Panel exclusivo para calibrar la IA (usando *Depth Anything V2*), capturar fotos de referencia, probar sensibilidad y exportar datasets de entrenamiento.
*   **Seguridad Avanzada:** Autenticación mediante tokens JWT en cookies `httpOnly`, contraseñas encriptadas con `bcrypt`, y protección contra enumeración de usuarios.
*   **Auditoría y Reportes:** Registro automático de acciones críticas (creación de usuarios, empresas, cámaras) y generación de reportes de actividad descargables en formato `.txt`.
*   **Recuperación de Contraseña:** Flujo simulado sin dependencia de servidores SMTP, mostrando el código de seguridad directamente en pantalla para entornos de demostración.

## 🛠️ Stack Tecnológico

| Capa | Tecnologías Utilizadas |
| :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy (ORM), Uvicorn |
| **Base de Datos** | Neon.tech (Producción/Nube) / SQLite (Desarrollo local) |
| **Frontend** | HTML5, CSS3 nativo, JavaScript (Vanilla ES6+), hls.js |
| **Visión por Computador** | Ultralytics (YOLOv8), OpenCV, PyTorch, Transformers (Depth Anything V2) |
| **Despliegue / Edge** | NVIDIA Jetson Orin NX, Playwright (Headless Chromium), Docker (Opcional) |

## 📂 Estructura del Proyecto

```text
ia_proyecto_titulo v1.5/
│
├── base_de_datos/          # Capa de datos (Modelos SQLAlchemy y CRUDs)
├── deepseek/               # Módulos de Inteligencia Artificial y Visión
├── templates/              # Archivos HTML (Jinja2)
├── static/                 # Archivos CSS y JavaScript del frontend
│
├── main.py                 # Aplicación principal FastAPI (Rutas y Lógica)
├── requirements.txt        # Dependencias del proyecto
├── iniciar.bat             # Script de arranque rápido para Windows
└── README.md               # Documentación del repositorio
```

## ☁️ Despliegue en la Nube

El proyecto utiliza una arquitectura de nube dividida en dos servicios:

*   **Backend (Render):** La aplicación FastAPI se despliega como un Web Service en [Render](https://render.com). La configuración de arranque (Build Command y Start Command) se define directamente desde el panel web de Render.
*   **Base de Datos (Neon.tech):** La base de datos se aloja en [Neon.tech](https://neon.tech), un servicio serverless. La conexión se establece mediante la variable de entorno `DATABASE_URL`, configurada en el panel de Render.

## 🔑 Credenciales de Prueba

Los siguientes usuarios están disponibles en el entorno de demostración:

| Usuario | Contraseña | Rol |
| :--- | :--- | :--- |
| `admin` | `admin1234` | Administrador |
| `supervisor` | `super1234` | Supervisor |
| `demo` | `demo1234` | Usuario |
| `learning` | `learning1234` | Learning |

## 🧪 Pruebas Realizadas

Se verificó el flujo completo de gestión de usuarios con auditoría:

1.  **Crear** un nuevo usuario desde el panel de administración.
2.  **Editar** sus datos (nombre, rol, empresa asignada).
3.  **Desactivar** la cuenta del usuario.
4.  **Intentar iniciar sesión** con la cuenta desactivada (resultado esperado: fallo con mensaje de acceso denegado).
5.  **Eliminar** definitivamente el usuario del sistema.
6.  **Verificar el reporte de auditoría**, confirmando que cada acción quedó registrada con su timestamp y el usuario responsable.
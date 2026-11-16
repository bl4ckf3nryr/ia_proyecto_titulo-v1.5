# 📦 Gestor de Bultos - Monitoreo Edge-to-Cloud

**Gestor de Bultos** es una solución integral de software diseñada para brindar visibilidad en tiempo real sobre el estado de ocupación física de los sectores de bodega en Centros de Distribución (CD).

El sistema integra visión por computador (Edge Computing) con un backend centralizado en la nube, permitiendo a supervisores y jefaturas tomar decisiones informadas sobre el uso del espacio sin depender de inspecciones manuales.

## 🚀 Características Principales

*   **Arquitectura Edge-to-Cloud:** Utiliza un Edge Device (NVIDIA Jetson Orin NX) con el modelo **YOLOv8** para procesar video localmente sin depender de la nube, enviando solo los datos relevantes al servidor.
*   **Sistema de Roles y Aislamiento:** Control de acceso basado en roles (`admin`, `supervisor`, `usuario`, `learning`). Cada supervisor y usuario solo visualiza la información de su propia empresa (Multi-tenant).
*   **Visualización en Tiempo Real:** Dashboard web con integración de cámaras IP vía HLS, MJPEG y RTSP (procesado por el servidor).
*   **Módulo de Inteligencia Artificial (Learning):** Panel exclusivo para calibrar la IA (usando *Depth Anything V2*), capturar fotos de referencia, probar sensibilidad y exportar datasets de entrenamiento.
*   **Seguridad Avanzada:** Autenticación mediante tokens JWT en cookies `httpOnly`, contraseñas encriptadas con `bcrypt`, y protección contra enumeración de usuarios.
*   **Auditoría y Reportes:** Registro automático de acciones críticas (creación de usuarios, empresas, cámaras) y generación de reportes de actividad descargables en formato `.txt`.
*   **Recuperación de Contraseña:** Flujo simulado sin dependencia de servidores SMTP, mostrando el código de seguridad directamente en pantalla para entornos de demostración.

## 🛠️ Stack Tecnológico

| Capa | Tecnologías Utilizadas |
| :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy (ORM), Uvicorn |
| **Base de Datos** | PostgreSQL (Producción/Nube) / SQLite (Desarrollo local) |
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
├── README.md               # Documentación del repositorio
└── render.yaml             # Configuración de despliegue en la nube
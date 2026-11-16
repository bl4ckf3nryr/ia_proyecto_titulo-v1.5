import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Leer la variable de entorno. En Render usará la URL de Neon.
# En tu PC, al no existir la variable, usará "sqlite:///./login.db".
URL_BASE_DATOS = os.environ.get("DATABASE_URL", "sqlite:///./login.db")

# 2. Render (y algunos servicios) a veces dan la URL con "postgres://". 
# SQLAlchemy 2.x exige que sea "postgresql://".
if URL_BASE_DATOS.startswith("postgres://"):
    URL_BASE_DATOS = URL_BASE_DATOS.replace("postgres://", "postgresql://", 1)

# 3. Configurar el motor (engine) según la base de datos
if URL_BASE_DATOS.startswith("sqlite"):
    # Configuración exclusiva para SQLite (desarrollo local)
    motor = create_engine(
        URL_BASE_DATOS,
        connect_args={"check_same_thread": False},
    )
else:
    # Configuración para PostgreSQL (producción en la nube)
    motor = create_engine(URL_BASE_DATOS)

SesionLocal = sessionmaker(bind=motor, autoflush=False, autocommit=False)

# Único Base para TODO el proyecto
Base = declarative_base()


def obtener_sesion():
    """Dependency de FastAPI: abre y cierra una sesión por request."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


def crear_tablas() -> None:
    """Crea las tablas si no existen."""
    from base_de_datos import modelos  # noqa: F401  (registra los modelos en Base)
    Base.metadata.create_all(bind=motor)
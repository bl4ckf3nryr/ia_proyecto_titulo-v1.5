from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

URL_BASE_DATOS = "sqlite:///./login.db"

motor = create_engine(
    URL_BASE_DATOS,
    connect_args={"check_same_thread": False},
)

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
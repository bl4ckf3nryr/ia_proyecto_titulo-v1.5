from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from base_de_datos.conexion import Base   # ← importamos el Base ÚNICO


class EmpresaORM(Base):
    __tablename__ = "empresas"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String, nullable=False, unique=True, index=True)
    esta_activa = Column(Boolean, default=True)


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id                 = Column(Integer, primary_key=True, index=True)
    nombre             = Column(String, nullable=False)
    email              = Column(String, nullable=False, unique=True, index=True)
    password_hasheada  = Column(String, nullable=False)
    esta_activo        = Column(Boolean, default=True)
    rol                = Column(String, nullable=False, default="usuario")
    empresa_id         = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    reset_code         = Column(String, nullable=True)
    reset_code_expira  = Column(DateTime, nullable=True)


class DepartamentoORM(Base):
    __tablename__ = "departamentos"

    id         = Column(Integer, primary_key=True, index=True)
    nombre     = Column(String, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)


class CamaraORM(Base):
    __tablename__ = "camaras"

    id              = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String, nullable=False)
    url_stream      = Column(String, nullable=False)
    esta_activa     = Column(Boolean, default=True)
    empresa_id      = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=False, index=True)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)


class AuditoriaORM(Base):
    __tablename__ = "auditoria"

    id            = Column(Integer, primary_key=True, index=True)
    usuario_email = Column(String, nullable=False, default="Sistema")
    accion        = Column(String, nullable=False, index=True)
    detalle       = Column(String, nullable=False, default="")
    fecha_hora    = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

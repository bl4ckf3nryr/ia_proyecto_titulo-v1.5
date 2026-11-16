from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from base_de_datos.modelos import UsuarioORM


def obtener_por_email(sesion: Session, email: str) -> Optional[UsuarioORM]:
    return (
        sesion.query(UsuarioORM)
        .filter(UsuarioORM.email == email.lower())
        .first()
    )


def obtener_por_id(sesion: Session, usuario_id: int) -> Optional[UsuarioORM]:
    return sesion.query(UsuarioORM).filter(UsuarioORM.id == usuario_id).first()


def listar_usuarios(sesion: Session) -> List[UsuarioORM]:
    return sesion.query(UsuarioORM).order_by(UsuarioORM.id.asc()).all()


def listar_usuarios_por_empresa(sesion: Session, empresa_id: int) -> List[UsuarioORM]:
    return (
        sesion.query(UsuarioORM)
        .filter(UsuarioORM.empresa_id == empresa_id)
        .order_by(UsuarioORM.id.asc())
        .all()
    )


def listar_usuarios_por_rol(sesion: Session, rol: str) -> List[UsuarioORM]:
    return (
        sesion.query(UsuarioORM)
        .filter(UsuarioORM.rol == rol)
        .order_by(UsuarioORM.id.asc())
        .all()
    )


def crear_usuario(
    sesion: Session,
    email: str,
    password_hasheada: str,
    nombre: str = "",
    esta_activo: bool = True,
    rol: str = "usuario",
    empresa_id: Optional[int] = None,
) -> UsuarioORM:
    usuario = UsuarioORM(
        nombre=nombre.strip(),
        email=email.lower(),
        password_hasheada=password_hasheada,
        esta_activo=esta_activo,
        rol=rol,
        empresa_id=empresa_id,
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)
    return usuario


def guardar_codigo_reset(
    sesion: Session,
    usuario_id: int,
    codigo: str,
    fecha_expiracion: datetime,
) -> None:
    usuario = sesion.query(UsuarioORM).filter(UsuarioORM.id == usuario_id).first()
    if usuario:
        usuario.reset_code = codigo
        usuario.reset_code_expira = fecha_expiracion
        sesion.commit()


def actualizar_password(
    sesion: Session,
    usuario_id: int,
    nueva_password_hasheada: str,
) -> None:
    usuario = sesion.query(UsuarioORM).filter(UsuarioORM.id == usuario_id).first()
    if usuario:
        usuario.password_hasheada = nueva_password_hasheada
        usuario.reset_code = None
        usuario.reset_code_expira = None
        sesion.commit()


def actualizar_usuario(
    sesion: Session,
    usuario_id: int,
    datos: dict,
) -> Optional[UsuarioORM]:
    """
    Actualiza los campos permitidos de un usuario.
    `datos` puede contener: nombre, rol, empresa_id, esta_activo.
    Nunca toca email ni password_hasheada.
    Devuelve el usuario actualizado o None si no existe.
    """
    usuario = sesion.query(UsuarioORM).filter(UsuarioORM.id == usuario_id).first()
    if not usuario:
        return None

    campos_permitidos = {"nombre", "rol", "empresa_id", "esta_activo"}
    for campo, valor in datos.items():
        if campo in campos_permitidos:
            if campo == "nombre" and isinstance(valor, str):
                valor = valor.strip()
            setattr(usuario, campo, valor)

    sesion.commit()
    sesion.refresh(usuario)
    return usuario


def eliminar_usuario(sesion: Session, usuario_id: int) -> bool:
    """
    Elimina un usuario de la base de datos.
    Devuelve True si se eliminó, False si no existía.
    """
    usuario = sesion.query(UsuarioORM).filter(UsuarioORM.id == usuario_id).first()
    if not usuario:
        return False

    sesion.delete(usuario)
    sesion.commit()
    return True

from typing import List, Optional

from sqlalchemy.orm import Session

from base_de_datos.modelos import EmpresaORM


def crear_empresa(
    sesion: Session,
    nombre: str,
    esta_activa: bool = True,
) -> EmpresaORM:
    empresa = EmpresaORM(
        nombre=nombre.strip(),
        esta_activa=esta_activa,
    )
    sesion.add(empresa)
    sesion.commit()
    sesion.refresh(empresa)
    return empresa


def obtener_por_id(sesion: Session, empresa_id: int) -> Optional[EmpresaORM]:
    return sesion.query(EmpresaORM).filter(EmpresaORM.id == empresa_id).first()


def obtener_por_nombre(sesion: Session, nombre: str) -> Optional[EmpresaORM]:
    return sesion.query(EmpresaORM).filter(EmpresaORM.nombre == nombre.strip()).first()


def listar_empresas(sesion: Session) -> List[EmpresaORM]:
    return sesion.query(EmpresaORM).order_by(EmpresaORM.id.asc()).all()


def listar_empresas_activas(sesion: Session) -> List[EmpresaORM]:
    return (
        sesion.query(EmpresaORM)
        .filter(EmpresaORM.esta_activa == True)  # noqa: E712
        .order_by(EmpresaORM.id.asc())
        .all()
    )


def actualizar_empresa(
    sesion: Session,
    empresa_id: int,
    nombre: Optional[str] = None,
    esta_activa: Optional[bool] = None,
) -> Optional[EmpresaORM]:
    """
    Actualiza nombre y/o estado activo de una empresa.
    Solo modifica los campos que se pasen como no-None.
    Devuelve la empresa actualizada o None si no existe.
    """
    empresa = sesion.query(EmpresaORM).filter(EmpresaORM.id == empresa_id).first()
    if not empresa:
        return None

    if nombre is not None:
        empresa.nombre = nombre.strip()
    if esta_activa is not None:
        empresa.esta_activa = esta_activa

    sesion.commit()
    sesion.refresh(empresa)
    return empresa


def eliminar_empresa(sesion: Session, empresa_id: int) -> bool:
    """
    Elimina una empresa de la base de datos.
    Devuelve True si se eliminó, False si no existía.
    La verificación de dependencias (usuarios, cámaras) debe hacerse
    antes de llamar a esta función, en la capa de endpoints.
    """
    empresa = sesion.query(EmpresaORM).filter(EmpresaORM.id == empresa_id).first()
    if not empresa:
        return False

    sesion.delete(empresa)
    sesion.commit()
    return True

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

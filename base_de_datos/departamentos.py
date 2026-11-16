from typing import List, Optional

from sqlalchemy.orm import Session

from base_de_datos.modelos import DepartamentoORM


def crear_departamento(
    sesion: Session,
    nombre: str,
    empresa_id: int,
) -> DepartamentoORM:
    departamento = DepartamentoORM(
        nombre=nombre.strip(),
        empresa_id=empresa_id,
    )
    sesion.add(departamento)
    sesion.commit()
    sesion.refresh(departamento)
    return departamento


def obtener_por_id(sesion: Session, departamento_id: int) -> Optional[DepartamentoORM]:
    return (
        sesion.query(DepartamentoORM)
        .filter(DepartamentoORM.id == departamento_id)
        .first()
    )


def listar_por_empresa(sesion: Session, empresa_id: int) -> List[DepartamentoORM]:
    return (
        sesion.query(DepartamentoORM)
        .filter(DepartamentoORM.empresa_id == empresa_id)
        .order_by(DepartamentoORM.id.asc())
        .all()
    )

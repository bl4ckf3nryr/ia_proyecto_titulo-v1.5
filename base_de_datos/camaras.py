from typing import List, Optional

from sqlalchemy.orm import Session

from base_de_datos.modelos import CamaraORM


def crear_camara(
    sesion: Session,
    nombre: str,
    url_stream: str,
    empresa_id: int,
    departamento_id: int,
    usuario_id: Optional[int] = None,
    esta_activa: bool = True,
) -> CamaraORM:
    camara = CamaraORM(
        nombre=nombre.strip(),
        url_stream=url_stream.strip(),
        empresa_id=empresa_id,
        departamento_id=departamento_id,
        usuario_id=usuario_id,
        esta_activa=esta_activa,
    )
    sesion.add(camara)
    sesion.commit()
    sesion.refresh(camara)
    return camara


def obtener_por_id(sesion: Session, camara_id: int) -> Optional[CamaraORM]:
    return sesion.query(CamaraORM).filter(CamaraORM.id == camara_id).first()


def listar_por_empresa(sesion: Session, empresa_id: int) -> List[CamaraORM]:
    return (
        sesion.query(CamaraORM)
        .filter(CamaraORM.empresa_id == empresa_id)
        .order_by(CamaraORM.id.asc())
        .all()
    )


def listar_por_usuario(sesion: Session, usuario_id: int) -> List[CamaraORM]:
    return (
        sesion.query(CamaraORM)
        .filter(CamaraORM.usuario_id == usuario_id)
        .order_by(CamaraORM.id.asc())
        .all()
    )


def listar_por_departamento(sesion: Session, departamento_id: int) -> List[CamaraORM]:
    return (
        sesion.query(CamaraORM)
        .filter(CamaraORM.departamento_id == departamento_id)
        .order_by(CamaraORM.id.asc())
        .all()
    )


def actualizar_camara(
    sesion: Session,
    camara_id: int,
    **campos,
) -> Optional[CamaraORM]:
    camara = obtener_por_id(sesion, camara_id)
    if camara is None:
        return None
    campos_validos = {
        "nombre",
        "url_stream",
        "empresa_id",
        "departamento_id",
        "usuario_id",
        "esta_activa",
    }
    for campo, valor in campos.items():
        if campo in campos_validos:
            setattr(camara, campo, valor)
    sesion.commit()
    sesion.refresh(camara)
    return camara
from datetime import datetime

from sqlalchemy.orm import Session

from base_de_datos.modelos import AuditoriaORM


def registrar_accion(
    sesion: Session,
    usuario_email: str,
    accion: str,
    detalle: str = "",
) -> AuditoriaORM:
    """Guarda un registro de auditoría en la BD (fecha en UTC naive)."""
    registro = AuditoriaORM(
        usuario_email=usuario_email,
        accion=accion,
        detalle=detalle,
        fecha_hora=datetime.utcnow(),
    )
    sesion.add(registro)
    sesion.commit()
    sesion.refresh(registro)
    return registro


def listar_todas(sesion: Session) -> list[AuditoriaORM]:
    """Devuelve todos los registros ordenados por fecha descendente."""
    return (
        sesion.query(AuditoriaORM)
        .order_by(AuditoriaORM.fecha_hora.desc())
        .all()
    )

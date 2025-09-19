from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal


class Caja(BaseModel):
    id: str | None = None  # ID de base de datos
    folio: str | None = None # Folio legible (ej. "CAJA-0012")
    usuario_id: str        # Usuario o cajero que abrió la caja
    sucursal_id: str       # A qué sucursal pertenece
    fecha_apertura: datetime      # Al abrir caja
    fecha_cierre: datetime | None = None  # Al cerrar caja
    venta_total: Decimal | None = None
    estado: str = "abierta"         # "abierta", "cerrada"
    cortes_ids: list[str] = []
    tipo_cambio: float
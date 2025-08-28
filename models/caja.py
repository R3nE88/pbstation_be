from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
from models.movimiento_caja import MovimientoCaja  # Importar el modelo MovimientoCaja


class Caja(BaseModel):
    id: str | None = None  # ID de base de datos
    folio: str | None = None # Folio legible (ej. "CAJA-0012")
    usuario_id: str        # Usuario o cajero que abrió la caja
    sucursal_id: str       # A qué sucursal pertenece
    fecha_apertura: str    # Al abrir caja
    fecha_cierre: str | None = None  # Al cerrar caja
    efectivo_apertura: Decimal       # Monto inicial en caja
    efectivo_cierre: Decimal | None = None  # Monto contado al cerrar
    total_teorico: Decimal | None = None    # Lo que debería haber
    diferencia: Decimal | None = None       # efectivo_cierre - total_teorico
    estado: str = "abierta"         # "abierta", "cerrada"
    ventas_ids: list[str] = []      # Referencia a ventas registradas
    movimiento_caja: list[MovimientoCaja] = []  # Movimientos de caja detalles: list[DetalleVenta]
    observaciones: str | None = None  # Comentarios o notas del cajero
    contadores: dict[str, dict[str, int]] = {}
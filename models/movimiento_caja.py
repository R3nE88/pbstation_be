from pydantic import BaseModel
from decimal import Decimal
from typing import Literal

class MovimientoCaja(BaseModel):
    id: str | None = None
    usuario_id: str           # Quién registró el movimiento
    tipo: Literal['entrada', 'retiro']  # Entrada o salida
    monto: float            # Monto del movimiento
    motivo: str               # Justificación breve (ej: "Pago proveedor", "Ajuste")
    fecha: str                # fecha de registro del movimiento
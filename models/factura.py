from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal

class Factura(BaseModel):
    id: str | None = None  # ID de base de datos
    factura_id: str # ID facturama
    folio_venta: str
    uuid: str #id sat
    fecha: datetime
    receptor_rfc: str
    receptor_nombre: str
    subtotal: Decimal
    descuento: Decimal
    impuestos: Decimal
    total: Decimal
    is_global: bool = False
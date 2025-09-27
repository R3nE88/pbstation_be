from pydantic import BaseModel
from decimal import Decimal

class DetalleVenta(BaseModel): #Entidad #modelo
    producto_id: str
    cantidad: int
    ancho: float | None = None
    alto: float | None = None
    comentarios: str
    descuento: int
    descuento_aplicado: Decimal
    iva: Decimal
    subtotal: Decimal
    cotizacion_precio : Decimal | None = None
from pydantic import BaseModel
from decimal import Decimal

class DetalleVenta(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    producto_id: str
    cantidad: int
    ancho: float
    alto: float
    comentarios: str
    descuento: int
    iva: Decimal
    subtotal: Decimal
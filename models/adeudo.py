from pydantic import BaseModel
from decimal import Decimal

class Adeudo(BaseModel): #Entidad #modelo
    venta_id: str
    monto_pendiente: Decimal
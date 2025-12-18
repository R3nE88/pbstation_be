from pydantic import BaseModel
from decimal import Decimal

class Producto(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    codigo: int
    descripcion: str
    unidad_sat: str
    clave_sat: str
    precio: Decimal
    inventariable: bool = False
    imprimible: bool = False
    valor_impresion: int
    requiere_medida: bool
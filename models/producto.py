from pydantic import BaseModel
from decimal import Decimal


class Producto(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    codigo: int
    descripcion: str
    tipo: str
    categoria: str
    precio: Decimal
    inventariable: bool = False
    imprimible: bool = False
    valor_impresion: int
    requiere_medida: bool
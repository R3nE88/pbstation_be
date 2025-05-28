from pydantic import BaseModel


class Producto(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    codigo: str
    descripcion: str
    tipo: str
    categoria: str
    precio: float
    inventariable: bool = False
    imprimible: bool = False
    valor_impresion: int
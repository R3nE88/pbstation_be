from typing_extensions import Literal
from pydantic import BaseModel

class Usuario(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str
    telefono: int | None = None
    psw: str | None = None
    rol: Literal['vendedor', 'maquilador', 'administrativo'] | None = 'vendedor'
    permisos: Literal['normal', 'elevado', 'admin'] | None = 'normal'
    activo: bool = True
from pydantic import BaseModel

class Sucursal(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str
    telefono: str
    direccion: str
    localidad: str
    activo: bool = True

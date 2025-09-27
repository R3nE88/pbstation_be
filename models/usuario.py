from pydantic import BaseModel

class Usuario(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str
    telefono: int
    psw: str | None = None
    rol: str
    activo: bool = True
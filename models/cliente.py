from pydantic import BaseModel


class Cliente(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str | None = None
    telefono: str | None = None
    rfc: str | None = None
    #uso_cfdi: str | None = None
    regimen_fiscal: str | None = None
    codigo_postal: str | None = None
    direccion: str | None = None
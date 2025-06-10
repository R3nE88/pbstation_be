from pydantic import BaseModel


class Cliente(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str | None = None
    telefono: str | None = None
    razon_social: str | None = None
    rfc: str | None = None
    regimen_fiscal: str | None = None
    codigo_postal: str | None = None
    direccion: str | None = None
    no_ext: str | None = None
    no_int: str | None = None
    colonia: str | None = None
    localidad: str | None = None

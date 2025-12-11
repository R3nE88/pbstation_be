from pydantic import BaseModel

from models.adeudo import Adeudo

class Cliente(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    nombre: str
    correo: str | None = None
    telefono: int | None = None
    razon_social: str | None = None
    rfc: str | None = None
    regimen_fiscal: str | None = None
    codigo_postal: int | None = None
    direccion: str | None = None
    no_ext: int | None = None
    no_int: int | None = None
    colonia: str | None = None
    localidad: str | None = None
    adeudos: list[Adeudo] | None = None
    protegido: bool = False
    activo: bool = True
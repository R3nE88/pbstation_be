from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime

class MovimientoCaja(BaseModel):
    id: str | None = None
    usuario_id: str
    tipo: Literal['entrada', 'retiro']
    monto: float
    motivo: str
    fecha: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def validar_id(cls, v):
        # Asegurar que si viene como string, se mantiene
        if v == "":
            return None
        return v
    
    class Config:
        # Permitir campos extras que no estén en el modelo
        extra = 'ignore'
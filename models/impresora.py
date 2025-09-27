from typing import Dict, Optional
from pydantic import BaseModel

class Impresora(BaseModel):
    id: str | None = None
    numero: int
    modelo: str
    serie: str
    sucursal_id: str
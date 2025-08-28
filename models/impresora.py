from typing import Dict, Optional
from pydantic import BaseModel

class Impresora(BaseModel):
    id: Optional[str] = None   # opcional
    numero: int
    modelo: str
    serie: str
    sucursal_id: str

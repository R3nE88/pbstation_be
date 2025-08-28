from typing import Dict, Optional
from pydantic import BaseModel

class Contador(BaseModel):
    id: Optional[str] = None   # opcional
    impresora_id: str
    cantidad: int
    fecha: str

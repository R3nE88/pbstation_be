from typing import Dict, Optional
from pydantic import BaseModel

class Contador(BaseModel):
    id: str | None = None
    impresora_id: str
    cantidad: int
    fecha: str

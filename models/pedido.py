from typing_extensions import Literal
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Archivo(BaseModel):
    nombre: str
    ruta: str
    tipo: str
    tamano: Optional[int] = None

class Pedido(BaseModel):
    id: str | None = None  # ID de base de datos
    cliente_id: str
    usuario_id: str
    usuario_id_entrego: str | None = None #quien le entro al cliente
    sucursal_id: str
    venta_id: str
    venta_folio: str
    folio: str
    descripcion: str | None = None
    fecha: datetime
    fecha_entrega: datetime
    fecha_entregado: datetime | None = None
    archivos: List[Archivo]
    estado: Literal['enEspera', 'pendiente', 'produccion', 'terminado', 'enSucursal', 'entregado', 'cancelado'] | None = 'pendiente'
    cancelado: bool | None = False

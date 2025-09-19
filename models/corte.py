from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal
from models.movimiento_caja import MovimientoCaja  # Importar el modelo MovimientoCaja
from typing import List

class Desglose(BaseModel):
    denominacion: float
    cantidad: int

class Corte(BaseModel):
    id: str | None = None
    folio: str | None = None
    usuario_id: str       #usuario que realizo el corte
    usuario_id_cerro: str | None = None
    sucursal_id: str
    fecha_apertura: datetime | None = None
    fecha_corte: datetime | None = None          #cuando se realizo el corte
    contadores_finales: dict[str, int] | None = None  #contadores en el momento del corte
    fondo_inicial: Decimal | None = None
    proximo_fondo: Decimal | None = None  #efectivo que se retiro para dejar para el proximo corte
    conteo_pesos: Decimal | None = None
    conteo_dolares: Decimal | None = None
    conteo_debito: Decimal | None = None
    conteo_credito: Decimal | None = None
    conteo_transf: Decimal | None = None
    conteo_total: Decimal | None = None   #efectivo contado
    venta_pesos: Decimal | None = None
    venta_dolares: Decimal | None = None
    venta_debito: Decimal | None = None
    venta_credito: Decimal | None = None
    venta_transf: Decimal | None = None
    venta_total: Decimal | None = None    #total de venta
    diferencia: Decimal | None = None
    movimiento_caja: list[MovimientoCaja] = []  # Movimientos de caja 
    desglose_pesos: List[Desglose] | None = None
    desglose_dolares: List[Desglose] | None = None
    ventas_ids: list[str] = [] 
    comentarios: str | None = None
    is_cierre: bool #si este corte es el cierre
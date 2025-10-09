from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal
from models.detalle_venta import DetalleVenta  # Importar el modelo DetalleVenta

class Venta(BaseModel): #Entidad #modelo
    id: str | None = None
    folio: str | None = None
    cliente_id: str
    usuario_id: str
    sucursal_id: str
    pedido_pendiente: bool
    fecha_entrega: datetime | None = None
    detalles: list[DetalleVenta]
    fecha_venta: datetime | None = None
    comentarios_venta: str | None = None
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    tipo_tarjeta: str | None = None
    referencia_tarj: str | None = None
    referencia_trans: str | None = None
    recibido_mxn: Decimal | None = None
    recibido_us: Decimal | None = None
    recibido_tarj: Decimal | None = None
    recibido_trans: Decimal | None = None
    recibido_total: Decimal
    abonado_mxn: Decimal | None = None
    abonado_us: Decimal | None = None
    abonado_tarj: Decimal | None = None
    abonado_trans: Decimal | None = None
    abonado_total: Decimal
    cambio: Decimal
    liquidado: bool
    was_deuda: bool | None = None
    cancelado : bool | None = None
    motivo_cancelacion: str | None = None
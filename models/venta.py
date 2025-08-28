from pydantic import BaseModel
from decimal import Decimal
from models.detalle_venta import DetalleVenta  # Importar el modelo DetalleVenta


class Venta(BaseModel): #Entidad #modelo
    id: str | None = None
    folio: str | None = None
    cliente_id: str
    usuario_id: str
    sucursal_id: str
    caja_id: str
    pedido_pendiente: bool
    fecha_entrega: str | None = None
    detalles: list[DetalleVenta]
    fecha_venta: str | None = None
    tipo_pago: str | None = None
    comentarios_venta: str
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    tipo_tarjeta: str | None = None
    referencia_tarj: str | None = None
    referencia_trans: str | None = None
    recibido_efect: Decimal | None = None
    recibido_tarj: Decimal | None = None
    recibido_trans: Decimal | None = None
    recibido_total: Decimal | None = None
    abonado: Decimal | None = None
    cambio: Decimal | None = None
    liquidado: bool | None = None
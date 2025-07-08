from pydantic import BaseModel
from decimal import Decimal
from models.detalle_venta import DetalleVenta  # Importar el modelo DetalleVenta


class Venta(BaseModel): #Entidad #modelo
    id: str | None = None
    folio: str
    cliente_id: str
    usuario_id: str
    sucursal_id: str
    pedido_pendiente: bool
    fecha_entrega: str | None = None
    detalles: list[DetalleVenta]
    fecha_venta: str
    tipo_pago: str
    comentarios_venta: str
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    recibido: Decimal
    abonado: Decimal
    cambio: Decimal
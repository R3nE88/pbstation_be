from pydantic import BaseModel
from decimal import Decimal
from models.detalle_venta import DetalleVenta  # Importar el modelo DetalleVenta


class VentaEnviada(BaseModel): #Entidad #modelo
    id: str | None = None
    cliente_id: str
    usuario_id: str
    usuario: str
    sucursal_id: str
    pedido_pendiente: bool
    fecha_entrega: str | None = None
    detalles: list[DetalleVenta]
    comentarios_venta: str
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    fecha_envio: str
    compu: str
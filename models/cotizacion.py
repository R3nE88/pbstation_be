from pydantic import BaseModel
from decimal import Decimal
from models.detalle_venta import DetalleVenta  # Importar el modelo DetalleVenta


class Cotizacion(BaseModel): #Entidad #modelo
    id: str | None = None
    folio: str | None = None
    cliente_id: str
    usuario_id: str
    sucursal_id: str
    detalles: list[DetalleVenta]
    fecha_cotizacion: str
    comentarios_venta: str
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    vigente: bool

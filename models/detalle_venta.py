from pydantic import BaseModel


class DetalleVenta(BaseModel): #Entidad #modelo
    id: str | None = None  #None es opcional
    producto_id: str
    cantidad: int
    ancho: float
    alto: float
    comentarios: str
    descuento: int
    iva: float
    subtotal: float
def detalle_venta_schema(detalle_venta) -> dict:
    return {
        "id":str(detalle_venta["_id"]),
        "producto_id":detalle_venta["producto_id"],
        "cantidad":detalle_venta["cantidad"],
        "ancho":detalle_venta["ancho"],
        "alto":detalle_venta["alto"],
        "comentarios":detalle_venta["comentarios"],
        "descuento":detalle_venta["descuento"],
        "iva": float(detalle_venta["iva"].to_decimal()), 
        "subtotal": float(detalle_venta["subtotal"].to_decimal()), 
    }

def detalles_venta_schema(detalles_venta) -> list:
    return [detalle_venta_schema(detalle_venta) for detalle_venta in detalles_venta]


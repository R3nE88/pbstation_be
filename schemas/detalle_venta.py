def detalle_venta_schema(detalle_venta) -> dict:
    return {
        #"id":str(detalle_venta["_id"]),
        "producto_id":detalle_venta["producto_id"],
        "cantidad":detalle_venta["cantidad"],
        "ancho":detalle_venta["ancho"],
        "alto":detalle_venta["alto"],
        "comentarios":detalle_venta["comentarios"],
        "descuento":detalle_venta["descuento"],
        "descuento_aplicado":float(detalle_venta["descuento_aplicado"].to_decimal()),
        "iva": float(detalle_venta["iva"].to_decimal()), 
        "subtotal": float(detalle_venta["subtotal"].to_decimal()), 
        "total": float(detalle_venta["total"].to_decimal()), 
        "cotizacion_precio": float(detalle_venta["cotizacion_precio"].to_decimal()) if detalle_venta["cotizacion_precio"] else None
    }

def detalles_venta_schema(detalles_venta) -> list:
    return [detalle_venta_schema(detalle_venta) for detalle_venta in detalles_venta]
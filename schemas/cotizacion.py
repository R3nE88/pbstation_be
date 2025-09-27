from schemas.detalle_venta import detalles_venta_schema

def cotizacion_schema(cotizacion) -> dict:
    return {
        "id":str(cotizacion["_id"]),
        "folio": cotizacion["folio"],
        "cliente_id": cotizacion["cliente_id"],
        "usuario_id": cotizacion["usuario_id"],
        "sucursal_id": cotizacion["sucursal_id"],
        "detalles": detalles_venta_schema(cotizacion["detalles"]),
        "fecha_cotizacion": cotizacion["fecha_cotizacion"],
        "comentarios_venta": cotizacion["comentarios_venta"],
        "subtotal": float(cotizacion["subtotal"].to_decimal()), 
        "descuento": float(cotizacion["descuento"].to_decimal()), 
        "iva": float(cotizacion["iva"].to_decimal()), 
        "total": float(cotizacion["total"].to_decimal()), 
        "vigente": cotizacion["vigente"]
    }

def cotizaciones_schema(cotizaciones) -> list:
    return [cotizacion_schema(cotizacion) for cotizacion in cotizaciones]
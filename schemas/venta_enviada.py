from schemas.detalle_venta import detalles_venta_schema

def venta_enviada_schema(venta_enviada) -> dict:
    return {
        "id":str(venta_enviada["_id"]),
        "cliente_id": venta_enviada["cliente_id"],
        "usuario_id": venta_enviada["usuario_id"],
        "usuario": venta_enviada["usuario"],
        "sucursal_id": venta_enviada["sucursal_id"],
        "pedido_pendiente": venta_enviada["pedido_pendiente"],
        "fecha_entrega": venta_enviada["fecha_entrega"],
        "detalles": detalles_venta_schema(venta_enviada["detalles"]),
        "comentarios_venta": venta_enviada["comentarios_venta"],
        "subtotal": float(venta_enviada["subtotal"].to_decimal()), 
        "descuento": float(venta_enviada["descuento"].to_decimal()), 
        "iva": float(venta_enviada["iva"].to_decimal()), 
        "total": float(venta_enviada["total"].to_decimal()), 
        "fecha_envio": venta_enviada["fecha_envio"],
        "compu": venta_enviada["compu"]
    }

def ventas_enviadas_schema(ventas_enviadas) -> list:
    return [venta_enviada_schema(venta_enviada) for venta_enviada in ventas_enviadas]
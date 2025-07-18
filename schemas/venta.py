from schemas.detalle_venta import detalles_venta_schema

def venta_schema(venta) -> dict:
    return {
        "id":str(venta["_id"]),
        "folio": venta["folio"],
        "cliente_id": venta["cliente_id"],
        "usuario_id": venta["usuario_id"],
        "sucursal_id": venta["sucursal_id"],
        "pedido_pendiente": venta["pedido_pendiente"],
        "fecha_entrega": venta["fecha_entrega"],
        "detalles": detalles_venta_schema(venta["detalles"]),
        "fecha_venta": venta["fecha_venta"],
        "tipo_pago": venta["tipo_pago"],
        "comentarios_venta": venta["comentarios_venta"],
        "subtotal": float(venta["subtotal"].to_decimal()), 
        "descuento": float(venta["descuento"].to_decimal()), 
        "iva": float(venta["iva"].to_decimal()), 
        "total": float(venta["total"].to_decimal()), 
        "recibido": float(venta["recibido"].to_decimal()), 
        "abonado": float(venta["abonado"].to_decimal()), 
        "cambio": float(venta["cambio"].to_decimal()), 
        "liquidado": venta["liquidado"],
    }

def ventas_schema(ventas) -> list:
    return [venta_schema(venta) for venta in ventas]
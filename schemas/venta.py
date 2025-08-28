from schemas.detalle_venta import detalles_venta_schema

def decimal_to_float(value):
    return float(value.to_decimal()) if value is not None else None

def venta_schema(venta) -> dict:
    return {
        "id":str(venta["_id"]),
        "folio": venta["folio"],
        "cliente_id": venta["cliente_id"],
        "usuario_id": venta["usuario_id"],
        "sucursal_id": venta["sucursal_id"],
        "caja_id": venta["caja_id"],
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
        "tipo_tarjeta": venta["tipo_tarjeta"],
        "referencia_tarj": venta["referencia_tarj"],
        "referencia_trans": venta["referencia_trans"],
        "recibido_efect": decimal_to_float(venta["recibido_efect"]),
        "recibido_tarj": decimal_to_float(venta["recibido_tarj"]),
        "recibido_trans": decimal_to_float(venta["recibido_trans"]),
        "recibido_total": decimal_to_float(venta["recibido_total"]),
        "abonado": decimal_to_float(venta["abonado"]),
        "cambio": decimal_to_float(venta["cambio"]),
        "liquidado": venta["liquidado"],
    }


def ventas_schema(ventas) -> list:
    return [venta_schema(venta) for venta in ventas]
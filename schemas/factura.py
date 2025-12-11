def factura_schema(factura) -> dict:
    return {
        "id":str(factura["_id"]),
        "factura_id":factura["factura_id"],
        "venta_id":factura["venta_id"],
        "uuid":factura["uuid"],
        "fecha":factura["fecha"],
        "receptor_rfc":factura["receptor_rfc"],
        "receptor_nombre":factura["receptor_nombre"],
        "subtotal": float(factura["subtotal"].to_decimal()), 
        "impuestos": float(factura["impuestos"].to_decimal()), 
        "total": float(factura["total"].to_decimal()), 
    }

def facturas_schema(facturas) -> list:
    return [factura_schema(factura) for factura in facturas]
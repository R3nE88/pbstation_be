def factura_schema(factura) -> dict:
    return {
        "id":str(factura["_id"]),
        "factura_id":factura["factura_id"],
        "folio_venta":factura["folio_venta"],
        "uuid":factura["uuid"],
        "fecha":factura["fecha"],
        "receptor_rfc":factura["receptor_rfc"],
        "receptor_nombre":factura["receptor_nombre"],
        "subtotal": float(factura["subtotal"].to_decimal()), 
        "descuento": float(factura["descuento"].to_decimal()),
        "impuestos": float(factura["impuestos"].to_decimal()), 
        "total": float(factura["total"].to_decimal()), 
        "is_global": factura.get("is_global", False)
    }

def facturas_schema(facturas) -> list:
    return [factura_schema(factura) for factura in facturas]
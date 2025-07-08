def producto_schema(producto) -> dict:
    return {
        "id":str(producto["_id"]),
        "codigo":producto["codigo"],
        "descripcion":producto["descripcion"],
        "tipo":producto["tipo"],
        "categoria":producto["categoria"],
        "precio": float(producto["precio"].to_decimal()), 
        "inventariable":producto["inventariable"],
        "imprimible":producto["imprimible"],
        "valor_impresion":producto["valor_impresion"],
        "requiere_medida":producto["requiere_medida"]
    }

def productos_schema(productos) -> list:
    return [producto_schema(producto) for producto in productos]
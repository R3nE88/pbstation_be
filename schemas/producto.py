def producto_schema(producto) -> dict:
    return {
        "id":str(producto["_id"]),
        "codigo":producto["codigo"],
        "descripcion":producto["descripcion"],
        "tipo":producto["tipo"],
        "categoria":producto["categoria"],
        "precio":producto["precio"],
        "inventariable":producto["inventariable"],
        "imprimible":producto["imprimible"],
        "valor_impresion":producto["valor_impresion"],
    }

def productos_schema(productos) -> list:
    return [producto_schema(producto) for producto in productos]
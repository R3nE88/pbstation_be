def pedido_schema(pedido) -> dict:
    return {
        "id": str(pedido["_id"]),
        "cliente_id": pedido["cliente_id"],
        "usuario_id": pedido["usuario_id"],
        "sucursal_id": pedido["sucursal_id"],
        "venta_id": pedido["venta_id"],
        "folio": pedido["folio"],
        "descripcion": pedido.get("descripcion", ""),
        "fecha": pedido["fecha"],
        "fecha_entrega": pedido["fecha_entrega"],
        "archivos": pedido["archivos"],
        "estado": pedido.get("estado", "pendiente")
        
    }

def pedidos_schema(pedidos) -> list:
    return [pedido_schema(p) for p in pedidos]

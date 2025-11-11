def pedido_schema(pedido) -> dict:
    return {
        "id": str(pedido["_id"]),
        "cliente_id": pedido["cliente_id"],
        "usuario_id": pedido["usuario_id"],
        "usuario_id_entrego": pedido.get("usuario_id_entrego"),
        "sucursal_id": pedido["sucursal_id"],
        "venta_id": pedido["venta_id"],
        "venta_folio": pedido["venta_folio"],
        "folio": pedido["folio"],
        "descripcion": pedido.get("descripcion", ""),
        "fecha": pedido["fecha"],
        "fecha_entrega": pedido["fecha_entrega"],
        "fecha_entregado": pedido.get("fecha_entregado"),
        "archivos": pedido["archivos"],
        "estado": pedido.get("estado", "pendiente"),
        "cancelado": pedido["cancelado"]
        
    }

def pedidos_schema(pedidos) -> list:
    return [pedido_schema(p) for p in pedidos]

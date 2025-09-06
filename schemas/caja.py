def decimal_to_float(value):
    return float(value.to_decimal()) if value is not None else None

def caja_schema(caja) -> dict:
    return {
        "id":str(caja["_id"]),
        "folio": caja["folio"],
        "usuario_id": caja["usuario_id"],
        "sucursal_id": caja["sucursal_id"],
        "fecha_apertura": caja["fecha_apertura"],
        "fecha_cierre": caja["fecha_cierre"],
        #"fondo_inicial": float(caja["fondo_inicial"].to_decimal()),
        "venta_total": decimal_to_float(caja["venta_total"]),
        "estado": caja["estado"],
        #"ventas_ids": caja["ventas_ids"],
        "cortes_ids": caja["cortes_ids"],
        "tipo_cambio": caja["tipo_cambio"],
    }

def cajas_schema(cajas) -> list:
    return [caja_schema(caja) for caja in cajas]
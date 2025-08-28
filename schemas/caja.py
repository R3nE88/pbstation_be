from schemas.movimiento_caja import movimiento_cajas_schema


def caja_schema(caja) -> dict:
    return {
        "id":str(caja["_id"]),
        "folio": caja["folio"],
        "usuario_id": caja["usuario_id"],
        "sucursal_id": caja["sucursal_id"],
        "fecha_apertura": caja["fecha_apertura"],
        "fecha_cierre": caja["fecha_cierre"],
        "efectivo_apertura": float(caja["efectivo_apertura"].to_decimal()),
        "efectivo_cierre": float(caja["efectivo_cierre"].to_decimal()) if caja["efectivo_cierre"] is not None else None,
        "total_teorico": float(caja["total_teorico"].to_decimal()) if caja["total_teorico"] is not None else None,
        "diferencia": float(caja["diferencia"].to_decimal()) if caja["diferencia"] is not None else None,
        "estado": caja["estado"],
        "ventas_ids": caja["ventas_ids"],
        "movimiento_caja": movimiento_cajas_schema(caja["movimiento_caja"]), #caja["movimiento_caja"], "detalles": detalles_venta_schema(venta["detalles"]),
        "observaciones": caja["observaciones"],    
        "contadores": caja["contadores"],

    }

def cajas_schema(cajas) -> list:
    return [caja_schema(caja) for caja in cajas]
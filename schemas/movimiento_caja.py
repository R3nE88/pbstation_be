def movimiento_caja_schema(movimiento_caja) -> dict:
    return {
        "id":str(movimiento_caja["_id"]),
        "usuario_id": movimiento_caja["usuario_id"],
        "tipo": movimiento_caja["tipo"],
        "monto": float(movimiento_caja["monto"]),
        "motivo": movimiento_caja["motivo"],
        "fecha": movimiento_caja["fecha"],
    }

def movimiento_cajas_schema(movimiento_cajas) -> list:
    return [movimiento_caja_schema(movimiento_caja) for movimiento_caja in movimiento_cajas]
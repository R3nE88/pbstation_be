from schemas.movimiento_caja import movimiento_cajas_schema

def decimal_to_float(value):
    return float(value.to_decimal()) if value is not None else None

def corte_schema(corte) -> dict:
    return {
        "id":str(corte["_id"]),
        "folio": corte["folio"],
        "usuario_id": corte["usuario_id"],
        "usuario_id_cerro": corte["usuario_id_cerro"],
        "sucursal_id": corte["sucursal_id"],
        "fecha_apertura": corte["fecha_apertura"],
        "fecha_corte": corte["fecha_corte"],
        "contadores_finales": corte["contadores_finales"],
        "fondo_inicial": decimal_to_float(corte["fondo_inicial"]),
        "proximo_fondo": decimal_to_float(corte["proximo_fondo"]),
        "conteo_pesos": decimal_to_float(corte["conteo_pesos"]),
        "conteo_dolares": decimal_to_float(corte["conteo_dolares"]),
        "conteo_debito": decimal_to_float(corte["conteo_debito"]),
        "conteo_credito": decimal_to_float(corte["conteo_credito"]),
        "conteo_transf": decimal_to_float(corte["conteo_transf"]),
        "conteo_total": decimal_to_float(corte["conteo_total"]),
        "venta_pesos": decimal_to_float(corte["venta_pesos"]),
        "venta_dolares": decimal_to_float(corte["venta_dolares"]),
        "venta_debito": decimal_to_float(corte["venta_debito"]),
        "venta_debito": decimal_to_float(corte["venta_debito"]),
        "venta_transf": decimal_to_float(corte["venta_transf"]),
        "venta_total": decimal_to_float(corte["venta_total"]),
        "diferencia": decimal_to_float(corte["diferencia"]),
        "movimiento_caja": movimiento_cajas_schema(corte["movimiento_caja"]),
        "desglose_pesos": corte["desglose_pesos"],
        "desglose_dolares": corte["desglose_dolares"],
        "ventas_ids": [str(v_id) if hasattr(v_id, '_type') else str(v_id) for v_id in corte.get("ventas_ids", [])],
        "comentarios": corte["comentarios"],
        "is_cierre": corte["is_cierre"],
    }

def cortes_schema(cortes) -> list:
    return [corte_schema(corte) for corte in cortes]
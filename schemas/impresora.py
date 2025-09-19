def impresora_schema(impresora) -> dict:
    return {
        "id": str(impresora["_id"]) if impresora.get("_id") else None,
        "numero":impresora["numero"],
        "modelo":impresora["modelo"],
        "serie":impresora["serie"],
        "sucursal_id":impresora["sucursal_id"]
    }

def impresoras_schema(impresoras) -> list:
    return [impresora_schema(impresora) for impresora in impresoras]
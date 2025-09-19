def contador_schema(contador) -> dict:
    return {
        "id":str(contador["_id"]),
        "impresora_id":contador["impresora_id"],
        "cantidad":contador["cantidad"],
    }

def contadores_schema(contadores) -> list:
    return [contador_schema(contador) for contador in contadores]
def sucursal_schema(sucursal) -> dict:
    return {
        "id":str(sucursal["_id"]),
        "nombre":sucursal["nombre"],
        "correo":sucursal["correo"],
        "telefono":sucursal["telefono"],
        "direccion":sucursal["direccion"],
        "localidad":sucursal["localidad"],
        "activo":sucursal["activo"],
        
    }

def sucursales_schema(sucursales) -> list:
    return [sucursal_schema(sucursal) for sucursal in sucursales]
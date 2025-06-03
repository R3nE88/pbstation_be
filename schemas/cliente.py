def cliente_schema(cliente) -> dict:
    return {
        "id":str(cliente["_id"]),
        "nombre":cliente["nombre"],
        "correo":cliente["correo"],
        "telefono":cliente["telefono"],
        "rfc":cliente["rfc"],
        #"uso_cfdi":cliente["uso_cfdi"],
        "regimen_fiscal":cliente["regimen_fiscal"],
        "codigo_postal":cliente["codigo_postal"],
        "direccion":cliente["direccion"],
    }

def clientes_schema(clientes) -> list:
    return [cliente_schema(cliente) for cliente in clientes]
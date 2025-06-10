def cliente_schema(cliente) -> dict:
    return {
        "id":str(cliente["_id"]),
        "nombre":cliente["nombre"],
        "correo":cliente["correo"],
        "telefono":cliente["telefono"],
        "razon_social":cliente["razon_social"],
        "rfc":cliente["rfc"],
        "regimen_fiscal":cliente["regimen_fiscal"],
        "codigo_postal":cliente["codigo_postal"],
        "direccion":cliente["direccion"],
        "no_ext":cliente["no_ext"],
        "no_int":cliente["no_int"],
        "colonia":cliente["colonia"],
        "localidad":cliente["localidad"]
    }

def clientes_schema(clientes) -> list:
    return [cliente_schema(cliente) for cliente in clientes]
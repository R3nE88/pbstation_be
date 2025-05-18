def usuario_schema(usuario) -> dict:
    return {
        "id":str(usuario["_id"]),
        "nombre":usuario["nombre"],
        "correo":usuario["correo"],
        "psw":usuario["psw"],
        "rol":usuario["rol"],
        "sucursal_id":usuario["sucursal_id"],
    }

def usuarios_schema(usuarios) -> list:
    return [usuario_schema(usuario) for usuario in usuarios]
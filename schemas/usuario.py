def usuario_schema(usuario) -> dict:
    return {
        "id":str(usuario["_id"]),
        "nombre":usuario["nombre"],
        "correo":usuario["correo"],
        "telefono":usuario["telefono"],
        "psw":usuario["psw"],
        "rol":usuario["rol"],
        "permisos":usuario["permisos"],
        "activo":usuario["activo"],
    }

def usuario_public_schema(usuario) -> dict:
    return {
        "id": str(usuario["_id"]),
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "telefono": usuario.get("telefono"),
        "rol": usuario.get("rol", "vendedor"),
        "permisos": usuario.get("permisos", "normal"),
        "activo": usuario.get("activo", True),
    }

def usuarios_schema(usuarios) -> list:
    return [usuario_public_schema(usuario) for usuario in usuarios]

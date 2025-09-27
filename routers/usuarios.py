from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pymongo import ReturnDocument
from models.cambiar_psw import CambiarPassword
from models.usuario import Usuario
from core.database import db_client
from schemas.usuario import usuario_schema, usuarios_schema
from passlib.context import CryptContext
from routers.websocket import manager 
from validar_token import validar_token 

# Configuración para hashing de contraseñas
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except AttributeError:
    # Suprimir el error relacionado con bcrypt
    pwd_context = None

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("/all", response_model=list[Usuario])
async def obtener_usuarios(token: str = Depends(validar_token)):
    return usuarios_schema(db_client.local.usuarios.find({"activo": True}))

@router.get("/{id}") #path
async def obtener_usuario_path(id: str, token: str = Depends(validar_token)):
    return search_usuario("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves
    
@router.get("/") #Query
async def obtener_usuario_query(id: str, token: str = Depends(validar_token)):
    return search_usuario("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves

@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED) #post
async def crear_usuario(usuario: Usuario, token: str = Depends(validar_token)):
    usuario.correo = usuario.correo.lower()
    if type(search_usuario("correo", usuario.correo)) == Usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Este Correo ya está asociado a un Usuario')
    
    usuario.telefono = usuario.telefono
    if type(search_usuario("telefono", usuario.telefono)) == Usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Este Teléfono ya está asociado a un Usuario')

    usuario.correo = usuario.correo.lower()
    usuario_dict = dict(usuario)
    usuario_dict["psw"] = pwd_context.hash(usuario.psw)  # Encriptar la contraseña
    del usuario_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.usuarios.insert_one(usuario_dict).inserted_id #mongodb crea automaticamente el id como "_id"

    nuevo_usuario = usuario_schema(db_client.local.usuarios.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-usuario:{str(id)}") #Notificar a todos
    return Usuario(**nuevo_usuario) #el ** sirve para pasar los valores del diccionario

@router.put("/", response_model=Usuario, status_code=status.HTTP_200_OK)
async def actualizar_usuario(usuario: Usuario, token: str = Depends(validar_token)):
    if not usuario.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un usuario"
        )

    usuario_dict = dict(usuario)
    del usuario_dict["id"]
    
    # Eliminar el password del diccionario para no actualizarlo
    if "psw" in usuario_dict:
        del usuario_dict["psw"]
    
    try:
        result = db_client.local.usuarios.update_one(
            {"_id": ObjectId(usuario.id)}, 
            {"$set": usuario_dict}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail='No se encontró el usuario (put)'
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='No se encontró el usuario (put)'
        )

    await manager.broadcast(f"put-usuario:{str(ObjectId(usuario.id))}")
    return search_usuario("_id", ObjectId(usuario.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def delete_usuario(id: str, token: str = Depends(validar_token)):
    found = db_client.local.usuarios.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": {"activo": False}},
        return_document=ReturnDocument.AFTER
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
    else:
        await manager.broadcast(f"delete-usuario:{str(id)}") #Notificar a todos
        return {'message':'Desactivado con exito'}
    
@router.patch("/cambiar-password", status_code=status.HTTP_200_OK)
async def cambiar_password_seguro(datos: CambiarPassword, token: str = Depends(validar_token)):
    try:
        # Buscar el usuario actual
        usuario_actual = db_client.local.usuarios.find_one({"_id": ObjectId(datos.id)})
        
        if not usuario_actual:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail='No se encontró el usuario'
            )
        
        # Encriptar la nueva contraseña
        nueva_psw_encriptada = pwd_context.hash(datos.nueva_psw)
        
        # Actualizar la contraseña
        db_client.local.usuarios.update_one(
            {"_id": ObjectId(datos.id)},
            {"$set": {"psw": nueva_psw_encriptada}}
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Error interno del servidor'
        )

    #await manager.broadcast(f"patch-usuario-password:{datos.id}")
    return {"message": "Contraseña actualizada exitosamente"}

def search_usuario(field: str, key):
    try:
        usuario = db_client.local.usuarios.find_one({field: key})
        if not usuario:  # Verificar si no se encontró el usuario
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return Usuario(**usuario_schema(usuario))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar usuario: {str(e)}')

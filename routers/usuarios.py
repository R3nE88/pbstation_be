from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from models.usuario import Usuario
from core.database import db_client
from schemas.usuario import usuario_schema, usuarios_schema

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("/all", response_model=list[Usuario])
async def obtener_usuarios():
    return usuarios_schema(db_client.local.usuarios.find())

@router.get("/{id}") #path
async def obtener_usuario_path(id: str):
    return search_usuario("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves
    
@router.get("/") #Query
async def obtener_usuario_query(id: str):
    return search_usuario("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves


@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED) #post
async def crear_usuario(usuario: Usuario):
    if type(search_usuario("correo", usuario.correo)) == Usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='El Usuario ya existe')
    
    usuario_dict = dict(usuario)
    del usuario_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.usuarios.insert_one(usuario_dict).inserted_id #mongodb crea automaticamente el id como "_id"

    nuevo_usuario = usuario_schema(db_client.local.usuarios.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    return Usuario(**nuevo_usuario) #el ** sirve para pasar los valores del diccionario

@router.put("/", response_model=Usuario, status_code=status.HTTP_200_OK) #put
async def actualizar_usuario(usuario: Usuario):
    if not usuario.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un usuario" #se necesita enviar mismo id si no no actualiza
        )

    usuario_dict = dict(usuario)
    print('primer id:')
    print(usuario.id)
    del usuario_dict["id"] #eliminar id para no actualizar el id
    try:
        db_client.local.usuarios.find_one_and_replace({"_id":ObjectId(usuario.id)}, usuario_dict)

    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario (put)')

    return search_usuario("_id", ObjectId(usuario.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def detele_user(id: str):
    found = db_client.local.usuarios.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
    else:
        return {'message':'Eliminado con exito'} 
    

def search_usuario(field: str, key):
    try:
        usuario = db_client.local.usuarios.find_one({field: key})
        if not usuario:  # Verificar si no se encontró el usuario
            return None
        return Usuario(**usuario_schema(usuario))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar usuario: {str(e)}')

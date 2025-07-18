from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header, status, Depends
from dotenv import load_dotenv
import os
from models.usuario import Usuario
from core.database import db_client
from schemas.usuario import usuario_schema, usuarios_schema
from passlib.context import CryptContext

# Configuración para hashing de contraseñas
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except AttributeError:
    # Suprimir el error relacionado con bcrypt
    pwd_context = None

# Cargar variables de entorno desde config.env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.env")
load_dotenv(dotenv_path=dotenv_path)

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY = SECRET_KEY.strip()  # Eliminar espacios o saltos de línea

# Depuración: Imprimir el valor de SECRET_KEY
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no se cargó correctamente desde config.env")
SECRET_KEY = SECRET_KEY.strip()  # Eliminar espacios o saltos de línea

def validar_token(tkn: str = Header(None, description="El token de autorización es obligatorio")):
    if tkn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sin Authorizacion"
        )
    if tkn != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorizacion inválida"
        )

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("/all", response_model=list[Usuario])
async def obtener_usuarios(token: str = Depends(validar_token)):
    return usuarios_schema(db_client.local.usuarios.find())

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

    return Usuario(**nuevo_usuario) #el ** sirve para pasar los valores del diccionario

@router.put("/", response_model=Usuario, status_code=status.HTTP_200_OK) #put
async def actualizar_usuario(usuario: Usuario, token: str = Depends(validar_token)):
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
async def detele_user(id: str, token: str = Depends(validar_token)):
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

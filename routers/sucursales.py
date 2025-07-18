from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header, status, Depends
from dotenv import load_dotenv
import os
from core.database import db_client
from models.sucursal import Sucursal
from schemas.sucursal import sucursales_schema, sucursal_schema
from routers.websocket import manager 


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

router = APIRouter(prefix="/sucursales", tags=["sucursales"])

@router.get("/all", response_model=list[Sucursal])
async def obtener_sucursales(token: str = Depends(validar_token)):
    return sucursales_schema(db_client.local.sucursales.find())

@router.get("/{id}") #path
async def obtener_sucursal_path(id: str, token: str = Depends(validar_token)):
    return search_sucursal("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves

@router.get("/") #Query
async def obtener_sucursal_query(id: str, token: str = Depends(validar_token)):
    return search_sucursal("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves

@router.post("/", response_model=Sucursal, status_code=status.HTTP_201_CREATED) #post
async def crear_sucursal(sucursal: Sucursal, token: str = Depends(validar_token)):
    if sucursal.nombre is not None:
        if type(search_sucursal("nombre", sucursal.nombre)) == Sucursal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='La sucursal ya existe en la base de datos.')
        
    sucursal_dict = dict(sucursal)
    del sucursal_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.sucursales.insert_one(sucursal_dict).inserted_id #mongodb crea automaticamente el id como "_id"

    nueva_sucuesal = sucursal_schema(db_client.local.sucursales.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-sucursal:{str(id)}") #Notificar a todos

    return Sucursal(**nueva_sucuesal) #el ** sirve para pasar los valores del diccionario


@router.put("/", response_model=Sucursal, status_code=status.HTTP_200_OK) #put
async def actualizar_sucursal(sucursal: Sucursal, token: str = Depends(validar_token)):
    print(sucursal)
    if not sucursal.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar la sucursal" #se necesita enviar mismo id si no no actualiza
        )

    sucursal_dict = dict(sucursal)
    del sucursal_dict["id"] #eliminar id para no actualizar el id
    try:
        db_client.local.sucursales.find_one_and_replace({"_id":ObjectId(sucursal.id)}, sucursal_dict)

    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro sucursal (put)')
    
    await manager.broadcast(f"put-sucursal:{str(ObjectId(sucursal.id))}") #Notificar a todos

    return search_sucursal("_id", ObjectId(sucursal.id))


# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
# async def delete_sucursal(id: str, token: str = Depends(validar_token)):
#     found = db_client.local.sucursales.find_one_and_delete({"_id": ObjectId(id)})
#     if not found:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la sucursal')
#     else:
#         await manager.broadcast(f"delete-sucursal:{str(id)}") #Notificar a todos
#         return {'message':'Eliminado con exito'} 
    

def search_sucursal(field: str, key):
    try:
        sucursal = db_client.local.sucursales.find_one({field: key})
        if not sucursal:  # Verificar si no se encontró la sucursal
            return None
        return Sucursal(**sucursal_schema(sucursal))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar sucursal: {str(e)}')

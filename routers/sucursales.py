from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pymongo import ReturnDocument
from core.database import db_client
from generador_folio import obtener_siguiente_prefijo
from models.sucursal import Sucursal
from schemas.sucursal import sucursales_schema, sucursal_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/sucursales", tags=["sucursales"])
 
@router.get("/all", response_model=list[Sucursal])
async def obtener_sucursales(token: str = Depends(validar_token)):
    return sucursales_schema(db_client.local.sucursales.find({"activo": True}))

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

    # generar prefijo atómico y sobreeescribir cualquier input
    prefijo = obtener_siguiente_prefijo(db_client.local)
    sucursal_dict["prefijo_folio"] = prefijo

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

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def delete_sucursal(id: str, token: str = Depends(validar_token)):
    found = db_client.local.sucursales.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": {"activo": False}},
        return_document=ReturnDocument.AFTER
    )
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la sucursal')
    else:
        await manager.broadcast(f"delete-sucursal:{str(id)}") #Notificar a todos
        return {'message':'Desactivado con exito'}
    
def search_sucursal(field: str, key):
    try:
        sucursal = db_client.local.sucursales.find_one({field: key})
        if not sucursal:  # Verificar si no se encontró la sucursal
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")
        return Sucursal(**sucursal_schema(sucursal))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar sucursal: {str(e)}')

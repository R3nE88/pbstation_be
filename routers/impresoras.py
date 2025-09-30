from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Header, status, Depends
from core.database import db_client
from models.impresora import Impresora
from schemas.impresora import impresoras_schema, impresora_schema
from routers.websocket import manager
from validar_token import validar_token 

router = APIRouter(prefix="/impresoras", tags=["impresoras"])

@router.get("/all", response_model=list[Impresora])
async def obtener_impresoras(token: str = Depends(validar_token)):
    return impresoras_schema(db_client.local.impresoras.find())

@router.get("/sucursal/{sucursal_id}", response_model=list[Impresora])
async def obtener_impresoras_sucursal(sucursal_id: str, token: str = Depends(validar_token)):
    impresoras = db_client.local.impresoras.find({"sucursal_id": sucursal_id})
    return impresoras_schema(impresoras)

@router.get("/{id}")
async def obtener_impresora(id: str, token: str = Depends(validar_token)):
    try:
        impresora = search_impresora("_id", ObjectId(id))
        if impresora is None:
            raise HTTPException(status_code=404, detail="Impresora no encontrada")
        return impresora
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")

@router.post("/", response_model=Impresora, status_code=status.HTTP_201_CREATED) #post
async def crear_impresora(impresora: Impresora, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    if type(search_impresora("serie", impresora.serie)) == Impresora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='La serie de la impresora ya existe, no se puede volver a ingresar la misma impresora')

    impresora_dict = dict(impresora)
    del impresora_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.impresoras.insert_one(impresora_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    
    nueva_impresora = impresora_schema(db_client.local.impresoras.find_one({"_id":id}))

    sucursal_id = impresora_dict.get("sucursal_id")
    await manager.broadcast_to_sucursal(
        f"post-impresora:{str(id)}",
        sucursal_id,
        exclude_connection_id=x_connection_id
    )
    return Impresora(**nueva_impresora) #el ** sirve para pasar los valores del diccionario

@router.put("/", response_model=Impresora, status_code=status.HTTP_200_OK) #put
async def actualizar_impresora(impresora: Impresora, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    if not impresora.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar la impresora" #se necesita enviar mismo id si no no actualiza
        )
    impresora_dict = impresora.model_dump() 
    del impresora_dict["id"]
    try:
        result = db_client.local.impresoras.find_one_and_replace(
            {"_id": ObjectId(impresora.id)}, 
            impresora_dict
        )
        if not result:
            raise HTTPException(status_code=404, detail='Impresora no encontrada.')
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    sucursal_id = impresora_dict.get("sucursal_id")
    await manager.broadcast_to_sucursal(
        f"put-impresora:{str(ObjectId(impresora.id))}",
        sucursal_id,
        exclude_connection_id=x_connection_id
    ) #Notificar a sucursal

    return search_impresora("_id", ObjectId(impresora.id))

@router.delete("/{id}/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detele_impresora(id: str, sucursal_id: str, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    found = db_client.local.impresoras.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la impresora')
    else:
        await manager.broadcast_to_sucursal(
            f"delete-impresora:{str(id)}",
            sucursal_id,
            exclude_connection_id=x_connection_id
        ) #Notificar a sucursal
        return {'message':'Eliminado con exito'} 
    
def search_impresora(field: str, key):
    try:
        impresora = db_client.local.impresoras.find_one({field: key})
        if not impresora:
            return None
        return Impresora(**impresora_schema(impresora)) 
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar impresora: {str(e)}')
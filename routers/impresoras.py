from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from core.database import db_client
from models.impresora import Impresora
from schemas.impresora import impresoras_schema, impresora_schema
from routers.websocket import manager
from validar_token import validar_token 

router = APIRouter(prefix="/impresoras", tags=["impresoras"])

@router.get("/all", response_model=list[Impresora])
async def obtener_impresoras(token: str = Depends(validar_token)):
    return impresoras_schema(db_client.local.impresoras.find())

@router.get("/{sucursal_id}", response_model=list[Impresora])
async def obtener_impresoras_sucursal(sucursal_id: str, token: str = Depends(validar_token)):
    impresoras = db_client.local.impresoras.find({"sucursal_id": sucursal_id})
    return impresoras_schema(impresoras)

@router.get("/{id}") #path
async def obtener_impresora_path(id: str, token: str = Depends(validar_token)):
    return search_impresora("_id", ObjectId(id))


@router.post("/", response_model=Impresora, status_code=status.HTTP_201_CREATED) #post
async def crear_impresora(impresora: Impresora, token: str = Depends(validar_token)):
    if type(search_impresora("serie", impresora.serie)) == Impresora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='La serie de la impresora ya existe, no se puede volver a ingresar la misma impresora')

    impresora_dict = dict(impresora)
    del impresora_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.impresoras.insert_one(impresora_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    
    nueva_impresora = impresora_schema(db_client.local.impresoras.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-impresora:{str(id)}") #Notificar a todos

    return Impresora(**nueva_impresora) #el ** sirve para pasar los valores del diccionario


@router.put("/", response_model=Impresora, status_code=status.HTTP_200_OK) #put
async def actualizar_impresora(impresora: Impresora, token: str = Depends(validar_token)):
    if not impresora.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar la impresora" #se necesita enviar mismo id si no no actualiza
        )

    impresora_dict = impresora.model_dump()
    del impresora_dict["id"]
    try:
        db_client.local.impresoras.find_one_and_replace({"_id":ObjectId(impresora.id)}, impresora_dict)
    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la impresora (put)')
    
    await manager.broadcast(f"put-impresora:{str(ObjectId(impresora.id))}") #Notificar a todos

    return search_impresora("_id", ObjectId(impresora.id))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def detele_impresora(id: str, token: str = Depends(validar_token)):
    found = db_client.local.impresoras.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la impresora')
    else:
        await manager.broadcast(f"delete-impresora:{str(id)}") #Notificar a todos
        return {'message':'Eliminado con exito'} 
    

def search_impresora(field: str, key):
    try:
        impresora = db_client.local.impresoras.find_one({field: key})
        if not impresora:  # Verificar si no se encontró la impresora
            return None
        return Impresora(**impresora_schema(impresora))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar impresora: {str(e)}')
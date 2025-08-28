from fastapi import APIRouter, HTTPException, Header, status, Depends
from typing import Optional
from core.database import db_client
from models.contador import Contador
from schemas.contador import contador_schema, contadores_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/contadores", tags=["Contadores"])

@router.get("/{impresora_id}", response_model=list[Contador])
async def obtener_contadores(impresora_id: str, token: str = Depends(validar_token)):
    contadores = db_client.local.contadores.find({"impresora_id": impresora_id})
    return contadores_schema(contadores)

@router.get("/ultimo/{impresora_id}", response_model=Optional[Contador])
async def obtener_ultimo_contador(impresora_id: str, token: str = Depends(validar_token)):
    ultimo = db_client.local.contadores.find_one(
        {"impresora_id": impresora_id},
        sort=[("fecha", -1)]
    )
    
    if not ultimo:
        raise HTTPException(status_code=404, detail="No se encontraron contadores para esta impresora")
    
    return contador_schema(ultimo)


@router.post("/", response_model=Contador, status_code=status.HTTP_201_CREATED) #post
async def crear_contador(contador: Contador, token: str = Depends(validar_token)):
    contador_dict = dict(contador)
    del contador_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.contadores.insert_one(contador_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    
    nuevo_contador = contador_schema(db_client.local.contadores.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-contador:{str(id)}") #Notificar a todos

    return Contador(**nuevo_contador) #el ** sirve para pasar los valores del diccionario


@router.delete("/{impresora_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_contadores_por_impresora(impresora_id: str, token: str = Depends(validar_token)):
    result = db_client.local.contadores.delete_many({"impresora_id": impresora_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron contadores para esta impresora"
        )
    #await manager.broadcast(f"delete-contadores:{impresora_id}")  # Notificar a todos
    return {"mensaje": f"Se eliminaron {result.deleted_count} contadores de la impresora {impresora_id}"}

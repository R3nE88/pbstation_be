from fastapi import APIRouter, HTTPException, Query, Response, status, Depends
from typing import List, Optional
from core.database import db_client
from models.contador import Contador
from schemas.contador import contador_schema, contadores_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/contadores", tags=["Contadores"])

#@router.get("/{impresora_id}", response_model=list[Contador])
#async def obtener_contador(impresora_id: str, token: str = Depends(validar_token)):
#    contadores = db_client.local.contadores.find({"impresora_id": impresora_id})
#    return contadores_schema(contadores)

#@router.get("/")
#async def obtener_contadores(
#    ids: List[str] = Query(..., description="Lista de IDs de impresoras"),
#    token: str = Depends(validar_token)
#):
#    cursor = db_client.local.contadores.find(
#        {"impresora_id": {"$in": ids}}
#    )
#    resultados = [
#        {"impresora_id": doc["impresora_id"], "cantidad": doc.get("cantidad", 0)}
#        for doc in cursor
#    ]
#    return resultados

@router.get("/ultimo/{impresora_id}", response_model=Optional[Contador])
async def obtener_ultimo_contador(impresora_id: str, token: str = Depends(validar_token)):
    ultimo = db_client.local.contadores.find_one(
        {"impresora_id": impresora_id},
        sort=[("fecha", -1)]
    )
    
    if not ultimo:
        raise HTTPException(status_code=404, detail="No se encontraron contadores para esta impresora")
    
    return contador_schema(ultimo)


@router.post("/{sucursal_id}", response_model=Contador, status_code=status.HTTP_201_CREATED) #post
async def crear_contador(sucursal_id: str, contador: Contador, token: str = Depends(validar_token)):
    contador_dict = dict(contador)
    del contador_dict["id"] #quitar el id para que no se guarde como null
    
    id = db_client.local.contadores.insert_one(contador_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nuevo_contador = contador_schema(db_client.local.contadores.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    impresora_id = contador_dict.get("impresora_id")
    await manager.broadcast_to_sucursal(f"post-contadores:{impresora_id}", sucursal_id) #Notificar a sucursal

    return Contador(**nuevo_contador) #el ** sirve para pasar los valores del diccionario


@router.delete("/{impresora_id}/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_contadores_por_impresora(impresora_id: str, sucursal_id: str, token: str = Depends(validar_token)):
    result = db_client.local.contadores.delete_many({"impresora_id": impresora_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron contadores para esta impresora"
        )
    await manager.broadcast_to_sucursal(f"delete-contadores:{impresora_id}", sucursal_id) #Notificar a sucursal
    return {"mensaje": f"Se eliminaron {result.deleted_count} contadores de la impresora {impresora_id}"}


@router.put("/actual/{impresora_id}/{sucursal_id}/{cantidad}")
async def sumar_contador(impresora_id: str, sucursal_id: str, cantidad: int, token: str = Depends(validar_token)):
    db_client.local.contadores.update_one(
        {"impresora_id": impresora_id},
        {"$inc": {"cantidad": cantidad}},  #{"$set": {"contador": cantidad}}, (inc: sumar, set:reemplazar)
        upsert=True
    )
    
    await manager.broadcast_to_sucursal(f"put-contadores:{impresora_id}", sucursal_id) #Notificar a sucursal
    return Response(status_code=204)

@router.put("/{impresora_id}/{sucursal_id}/{cantidad}")
async def actualizar_contador(impresora_id: str, sucursal_id: str, cantidad: int, token: str = Depends(validar_token)):
    db_client.local.contadores.update_one(
        {"impresora_id": impresora_id},
        {"$set": {"cantidad": cantidad}},  #{"$set": {"contador": cantidad}}, (inc: sumar, set:reemplazar)
        upsert=True
    )

    await manager.broadcast_to_sucursal(f"put-contadores:{impresora_id}", sucursal_id) #Notificar a sucursal
    return Response(status_code=204)
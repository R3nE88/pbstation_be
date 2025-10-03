from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status, Depends, Header
from typing import Optional
from core.database import db_client
from models.contador import Contador
from schemas.contador import contador_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/contadores", tags=["Contadores"])

@router.get("/{impresora_id}", response_model=Optional[Contador])
async def obtener_contador(impresora_id: str, token: str = Depends(validar_token)):
    ultimo = db_client.local.contadores.find_one({"impresora_id": impresora_id})
    if not ultimo:
        raise HTTPException(status_code=404, detail="No se encontraron contadores para esta impresora")
    return contador_schema(ultimo)

@router.post("/{sucursal_id}", response_model=Contador, status_code=status.HTTP_201_CREATED)
async def crear_contador(sucursal_id: str, contador: Contador, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    contador_dict = dict(contador)
    del contador_dict["id"]
    id = db_client.local.contadores.insert_one(contador_dict).inserted_id
    nuevo_contador = contador_schema(db_client.local.contadores.find_one({"_id":id}))
    impresora_id = contador_dict.get("impresora_id")
    await manager.broadcast_to_sucursal(
        f"post-contadores:{impresora_id}",
        sucursal_id,
        exclude_connection_id=x_connection_id
    )
    return Contador(**nuevo_contador)

@router.delete("/{impresora_id}/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_contadores_por_impresora(impresora_id: str, sucursal_id: str, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    result = db_client.local.contadores.delete_many({"impresora_id": impresora_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron contadores para esta impresora"
        )
    await manager.broadcast_to_sucursal(
        f"delete-contadores:{impresora_id}",
        sucursal_id,
        exclude_connection_id=x_connection_id
    )
    return {"mensaje": f"Se eliminaron {result.deleted_count} contadores de la impresora {impresora_id}"}

@router.put("/sumar/{impresora_id}/{sucursal_id}/{cantidad}")
async def sumar_contador(
    impresora_id: str,
    sucursal_id: str,
    cantidad: int,
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    contador_actualizado = db_client.local.contadores.find_one_and_update(
        {"impresora_id": impresora_id},
        {"$inc": {"cantidad": cantidad}},
        return_document=True
    )
    if not contador_actualizado:
        raise HTTPException(
            status_code=404,
            detail="No existe contador para esta impresora"
        )
    await manager.broadcast_to_sucursal(
        f"put-contadores:{impresora_id}",
        sucursal_id,
        exclude_connection_id=x_connection_id
    )
    return search_contador("_id", contador_actualizado["_id"])


@router.put("/{impresora_id}/{sucursal_id}/{cantidad}")
async def actualizar_contador(impresora_id: str, sucursal_id: str, cantidad: int, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    contador_actualizado = db_client.local.contadores.find_one_and_update(
        {"impresora_id": impresora_id},
        {"$set": {"cantidad": cantidad}},
        return_document=True  # Retorna el documento DESPUÉS de actualizarlo
    )
    if not contador_actualizado:
        raise HTTPException(
            status_code=404,
            detail="No existe contador para esta impresora"
        )
    await manager.broadcast_to_sucursal(
        f"put-contadores:{impresora_id}", 
        sucursal_id,
        exclude_connection_id=x_connection_id
    )
    return search_contador("_id", contador_actualizado["_id"])

def search_contador(field: str, key):
    try:
        contador = db_client.local.contadores.find_one({field: key})
        if not contador:
            return None
        return Contador(**contador_schema(contador)) 
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar contador: {str(e)}')
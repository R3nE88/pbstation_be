from typing import Optional
from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Header, status, Depends
from core.database import db_client
from models.adeudo import Adeudo
from models.cliente import Cliente
from schemas.cliente import clientes_schema, cliente_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.get("/all", response_model=list[Cliente])
async def obtener_clientes(token: str = Depends(validar_token)):
    return clientes_schema(db_client.local.clientes.find())

@router.get("/{id}")
async def obtener_cliente(id: str, token: str = Depends(validar_token)):
    try:
        clientes = search_cliente("_id", ObjectId(id))
        if clientes is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return clientes
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")

@router.post("/", response_model=Cliente, status_code=status.HTTP_201_CREATED) #post
async def crear_cliente(cliente: Cliente, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    if cliente.rfc is not None:
        if type(search_cliente("rfc", cliente.rfc)) == Cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='El cliente ya existe en la base de datos. (RFC)') 
    if cliente.razon_social is not None:
        if type(search_cliente("razon_social", cliente.razon_social)) == Cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='El cliente ya existe en la base de datos. (Razon Social)')
    cliente_dict = dict(cliente) #//TODO: no se si es mejor asi o usar cliente_dict = cliente.model_dump(), investigar
    del cliente_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.clientes.insert_one(cliente_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nuevo_cliente = cliente_schema(db_client.local.clientes.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar
    await manager.broadcast(
        f"post-cliente:{str(id)}", 
        exclude_connection_id=x_connection_id
    )
    return Cliente(**nuevo_cliente) #el ** sirve para pasar los valores del diccionario

@router.post("/{cliente_id}/adeudos", response_model=Cliente, status_code=status.HTTP_201_CREATED)
async def agregar_adeudo(cliente_id: str, adeudo: Adeudo, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    try:
        # Verificar que el cliente existe
        cliente_existente = db_client.local.clientes.find_one({"_id": ObjectId(cliente_id)})
        if not cliente_existente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail='Cliente no encontrado'
            )
        
        # Verificar si ya existe un adeudo con la misma venta_id
        cliente_obj = Cliente(**cliente_schema(cliente_existente))
        if cliente_obj.adeudos:
            for adeudo_existente in cliente_obj.adeudos:
                if adeudo_existente.venta_id == adeudo.venta_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Ya existe un adeudo para esta venta_id'
                    )
        
        # Preparar el adeudo para MongoDB (convertir Decimal a Decimal128)
        adeudo_dict = dict(adeudo)
        adeudo_dict["monto_pendiente"] = Decimal128(adeudo_dict["monto_pendiente"])
        
        # Agregar el nuevo adeudo usando $push
        db_client.local.clientes.update_one(
            {"_id": ObjectId(cliente_id)},
            {"$push": {"adeudos": adeudo_dict}}
        )
        
        # Obtener el cliente actualizado
        cliente_actualizado = search_cliente("_id", ObjectId(cliente_id))
        
        # Notificar a través de WebSocket
        await manager.broadcast(
            f"put-cliente:{cliente_id}",
            exclude_connection_id=x_connection_id
        )
        
        return cliente_actualizado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error al agregar adeudo: {str(e)}'
        )
    
@router.delete("/{cliente_id}/adeudos/{venta_id}", response_model=Cliente, status_code=status.HTTP_202_ACCEPTED)
async def eliminar_adeudo(cliente_id: str, venta_id: str, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    try:
        # Verificar que el cliente existe
        cliente_existente = db_client.local.clientes.find_one({"_id": ObjectId(cliente_id)})
        if not cliente_existente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail='Cliente no encontrado'
            )
        # Verificar si existe el adeudo con la venta_id especificada
        cliente_obj = Cliente(**cliente_schema(cliente_existente))
        adeudo_encontrado = False
        if cliente_obj.adeudos:
            for adeudo_existente in cliente_obj.adeudos:
                if adeudo_existente.venta_id == venta_id:
                    adeudo_encontrado = True
                    break
        if not adeudo_encontrado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Adeudo no encontrado para esta venta_id'
            )
        # Eliminar el adeudo usando $pull
        result = db_client.local.clientes.update_one(
            {"_id": ObjectId(cliente_id)},
            {"$pull": {"adeudos": {"venta_id": venta_id}}}
        )
        # Verificar que se eliminó correctamente
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='No se pudo eliminar el adeudo'
            )
        # Obtener el cliente actualizado
        cliente_actualizado = search_cliente("_id", ObjectId(cliente_id))
        # Notificar a través de WebSocket
        await manager.broadcast(
            f"put-cliente:{cliente_id}",
            exclude_connection_id=x_connection_id
        )
        return cliente_actualizado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error al eliminar adeudo: {str(e)}'
        )

@router.put("/", response_model=Cliente, status_code=status.HTTP_200_OK)
async def actualizar_cliente(cliente: Cliente, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    if not cliente.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un cliente"
        )
    cliente_dict = cliente.model_dump()
    del cliente_dict["id"]  # eliminar id para no actualizar el id
    if cliente_dict.get("adeudos"):
        for adeudo in cliente_dict["adeudos"]:
            if "monto_pendiente" in adeudo and adeudo["monto_pendiente"] is not None:
                adeudo["monto_pendiente"] = Decimal128(str(adeudo["monto_pendiente"]))
    try:
        result = db_client.local.clientes.find_one_and_replace(
            {"_id": ObjectId(cliente.id)}, 
            cliente_dict
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail='Cliente no encontrado'
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'Error al actualizar cliente: {str(e)}'
        )
    await manager.broadcast(
        f"put-cliente:{str(ObjectId(cliente.id))}",
        exclude_connection_id=x_connection_id
    )
    return search_cliente("_id", ObjectId(cliente.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def delete_cliente(id: str, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    found = db_client.local.clientes.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el cliente')
    else:
        await manager.broadcast(
            f"delete-cliente:{str(id)}",
            exclude_connection_id=x_connection_id
        ) #Notificar a todos
        return {'message':'Eliminado con exito'} 

def search_cliente(field: str, key):
    try:
        cliente = db_client.local.clientes.find_one({field: key})
        if not cliente:  # Verificar si no se encontró el cliente
            return None
        return Cliente(**cliente_schema(cliente))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar cliente: {str(e)}')
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from core.database import db_client
from models.cliente import Cliente
from schemas.cliente import clientes_schema, cliente_schema
from routers.websocket import manager 
from validar_token import validar_token 

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.get("/all", response_model=list[Cliente])
async def obtener_clientes(token: str = Depends(validar_token)):
    return clientes_schema(db_client.local.clientes.find())

@router.get("/{id}") #path
async def obtener_cliente_path(id: str, token: str = Depends(validar_token)):
    return search_cliente("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves

@router.get("/") #Query
async def obtener_cliente_query(id: str, token: str = Depends(validar_token)):
    return search_cliente("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves

@router.post("/", response_model=Cliente, status_code=status.HTTP_201_CREATED) #post
async def crear_cliente(cliente: Cliente, token: str = Depends(validar_token)):
    if cliente.rfc is not None:
        if type(search_cliente("rfc", cliente.rfc)) == Cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='El cliente ya existe en la base de datos. (RFC)')
        
    if cliente.razon_social is not None:
        if type(search_cliente("razon_social", cliente.razon_social)) == Cliente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='El cliente ya existe en la base de datos. (Razon Social)')

    cliente_dict = dict(cliente)
    del cliente_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.clientes.insert_one(cliente_dict).inserted_id #mongodb crea automaticamente el id como "_id"

    nuevo_cliente = cliente_schema(db_client.local.clientes.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-cliente:{str(id)}") #Notificar a todos

    return Cliente(**nuevo_cliente) #el ** sirve para pasar los valores del diccionario


@router.put("/", response_model=Cliente, status_code=status.HTTP_200_OK) #put
async def actualizar_cliente(cliente: Cliente, token: str = Depends(validar_token)):
    print(cliente)
    if not cliente.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un cliente" #se necesita enviar mismo id si no no actualiza
        )

    cliente_dict = dict(cliente)
    del cliente_dict["id"] #eliminar id para no actualizar el id
    try:
        db_client.local.clientes.find_one_and_replace({"_id":ObjectId(cliente.id)}, cliente_dict)

    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el cliente (put)')
    
    await manager.broadcast(f"put-cliente:{str(ObjectId(cliente.id))}") #Notificar a todos

    return search_cliente("_id", ObjectId(cliente.id))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def delete_cliente(id: str, token: str = Depends(validar_token)):
    found = db_client.local.clientes.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el cliente')
    else:
        await manager.broadcast(f"delete-cliente:{str(id)}") #Notificar a todos
        return {'message':'Eliminado con exito'} 
    

def search_cliente(field: str, key):
    try:
        cliente = db_client.local.clientes.find_one({field: key})
        if not cliente:  # Verificar si no se encontró el cliente
            return None
        return Cliente(**cliente_schema(cliente))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar cliente: {str(e)}')

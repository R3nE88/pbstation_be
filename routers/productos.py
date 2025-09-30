from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from core.database import db_client
from models.producto import Producto
from schemas.producto import productos_schema, producto_schema
from routers.websocket import manager 
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/all", response_model=list[Producto])
async def obtener_productos(token: str = Depends(validar_token)):
    return productos_schema(db_client.local.productos.find())

@router.get("/{id}")
async def obtener_producto(id: str, token: str = Depends(validar_token)):
    try:
        impresora = search_producto("_id", ObjectId(id))
        if impresora is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return impresora
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    producto: Producto, 
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    if type(search_producto("codigo", producto.codigo)) == Producto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail='El código del producto ya existe, no se puede repetir. Intenta otro.')

    producto_dict = dict(producto)
    del producto_dict["id"]
    producto_dict["precio"] = Decimal128(producto_dict["precio"])
    
    id = db_client.local.productos.insert_one(producto_dict).inserted_id

    nuevo_producto = producto_schema(db_client.local.productos.find_one({"_id":id}))
    
    await manager.broadcast(
        f"post-product:{str(id)}", 
        exclude_connection_id=x_connection_id
    )
    
    return Producto(**nuevo_producto)

@router.put("/", response_model=Producto, status_code=status.HTTP_200_OK)
async def actualizar_producto(
    producto: Producto, 
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)  # ID de conexión del cliente
):
    if not producto.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un producto"
        )
    producto_dict = producto.model_dump()
    del producto_dict["id"]
    producto_dict["precio"] = Decimal128(str(producto.precio))
    try:
        result = db_client.local.productos.find_one_and_replace(
            {"_id":ObjectId(producto.id)},
            producto_dict
        )
        if not result:
            raise HTTPException(status_code=404, detail='No se encontro el producto.')
    except:        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='No se encontro el producto (put)'
        )
    
    await manager.broadcast(
        f"put-product:{str(ObjectId(producto.id))}", 
        exclude_connection_id=x_connection_id
    )
    
    return search_producto("_id", ObjectId(producto.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def detele_producto(
    id: str, 
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)  # ID de conexión del cliente
):
    found = db_client.local.productos.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail='No se encontro el producto'
        )
    else:
        await manager.broadcast(
            f"delete-product:{str(id)}", 
            exclude_connection_id=x_connection_id
        )
        return {'message':'Eliminado con exito'} 
    
def search_producto(field: str, key):
    try:
        producto = db_client.local.productos.find_one({field: key})
        if not producto:
            return None
        return Producto(**producto_schema(producto))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'Error al buscar producto: {str(e)}'
        )
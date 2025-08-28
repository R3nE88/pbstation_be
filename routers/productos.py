from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
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

@router.get("/{id}") #path
async def obtener_producto_path(id: str, token: str = Depends(validar_token)):
    return search_producto("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves
    
@router.get("/") #Query
async def obtener_producto_query(id: str, token: str = Depends(validar_token)):
    return search_producto("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves


@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED) #post
async def crear_producto(producto: Producto, token: str = Depends(validar_token)):
    if type(search_producto("codigo", producto.codigo)) == Producto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='El código del producto ya existe, no se puede repetir. Intenta otro.')

    producto_dict = dict(producto)
    del producto_dict["id"] #quitar el id para que no se guarde como null
    producto_dict["precio"] = Decimal128(producto_dict["precio"])
    id = db_client.local.productos.insert_one(producto_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    

    nuevo_producto = producto_schema(db_client.local.productos.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    await manager.broadcast(f"post-product:{str(id)}") #Notificar a todos

    return Producto(**nuevo_producto) #el ** sirve para pasar los valores del diccionario


@router.put("/", response_model=Producto, status_code=status.HTTP_200_OK) #put
async def actualizar_producto(producto: Producto, token: str = Depends(validar_token)):
    print(producto)
    if not producto.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un producto" #se necesita enviar mismo id si no no actualiza
        )

    producto_dict = producto.model_dump()
    del producto_dict["id"]
    producto_dict["precio"] = Decimal128(str(producto.precio))
    try:
        db_client.local.productos.find_one_and_replace({"_id":ObjectId(producto.id)}, producto_dict)
    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el producto (put)')
    
    await manager.broadcast(f"put-product:{str(ObjectId(producto.id))}") #Notificar a todos

    return search_producto("_id", ObjectId(producto.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def detele_producto(id: str, token: str = Depends(validar_token)):
    found = db_client.local.productos.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el producto')
    else:
        await manager.broadcast(f"delete-product:{str(id)}") #Notificar a todos
        return {'message':'Eliminado con exito'} 
    

def search_producto(field: str, key):
    try:
        producto = db_client.local.productos.find_one({field: key})
        if not producto:  # Verificar si no se encontró el producto
            return None
        return Producto(**producto_schema(producto))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar producto: {str(e)}')

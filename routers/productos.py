from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from core.database import db_client
from models.producto import Producto
from schemas.producto import productos_schema, producto_schema


router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("/all", response_model=list[Producto])
async def obtener_productos():
    return productos_schema(db_client.local.productos.find())

@router.get("/{id}") #path
async def obtener_producto_path(id: str):
    return search_producto("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves
    
@router.get("/") #Query
async def obtener_producto_query(id: str):
    return search_producto("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves


@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED) #post
async def crear_producto(producto: Producto):
    if type(search_producto("codigo", producto.codigo)) == Producto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='El código del producto ya existe, no se puede repetir. Intenta otro.')

    producto_dict = dict(producto)
    del producto_dict["id"] #quitar el id para que no se guarde como null
    id = db_client.local.productos.insert_one(producto_dict).inserted_id #mongodb crea automaticamente el id como "_id"

    nuevo_producto = producto_schema(db_client.local.productos.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

    return Producto(**nuevo_producto) #el ** sirve para pasar los valores del diccionario

@router.put("/", response_model=Producto, status_code=status.HTTP_200_OK) #put
async def actualizar_producto(producto: Producto):
    if not producto.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un producto" #se necesita enviar mismo id si no no actualiza
        )

    producto_dict = dict(producto)
    print('primer id:')
    print(producto.id)
    del producto_dict["id"] #eliminar id para no actualizar el id
    try:
        db_client.local.productos.find_one_and_replace({"_id":ObjectId(producto.id)}, producto_dict)

    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el producto (put)')

    return search_producto("_id", ObjectId(producto.id))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def detele_producto(id: str):
    found = db_client.local.productos.find_one_and_delete({"_id": ObjectId(id)})
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el producto')
    else:
        return {'message':'Eliminado con exito'} 
    

def search_producto(field: str, key):
    try:
        producto = db_client.local.productos.find_one({field: key})
        if not producto:  # Verificar si no se encontró el producto
            return None
        return Producto(**producto_schema(producto))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar producto: {str(e)}')

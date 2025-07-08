# from bson import ObjectId
# from fastapi import APIRouter, HTTPException, Header, status, Depends
# from dotenv import load_dotenv
# import os
# from core.database import db_client
# from models.detalle_venta import DetalleVenta
# from schemas.detalle_venta import detalle_venta_schema, detalles_venta_schema
# from routers.websocket import manager 


# # Cargar variables de entorno desde config.env
# dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.env")
# load_dotenv(dotenv_path=dotenv_path)

# SECRET_KEY = os.getenv("SECRET_KEY")
# SECRET_KEY = SECRET_KEY.strip()  # Eliminar espacios o saltos de línea

# def validar_token(tkn: str = Header(None, description="El token de autorización es obligatorio")):
#     if tkn is None:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Sin Authorizacion"
#         )
#     if tkn != SECRET_KEY:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authorizacion inválida"
#         )

# router = APIRouter(prefix="/detalles_venta", tags=["detalles_venta"])


# @router.get("/all", response_model=list[DetalleVenta])
# async def obtener_detalle(token: str = Depends(validar_token)):
#     return detalles_venta_schema(db_client.local.detalles_venta.find())

# @router.get("/{id}") #path
# async def obtener_detalle_path(id: str, token: str = Depends(validar_token)):
#     return search_detalle("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves
    
# @router.get("/") #Query
# async def obtener_detalle_query(id: str, token: str = Depends(validar_token)):
#     return search_detalle("_id", ObjectId(id)) #objectid se usa porque el id de la base de datos no es un "_id":"id" si no algo poco mas complejo con mas llaves


# @router.post("/", response_model=DetalleVenta, status_code=status.HTTP_201_CREATED) #post
# async def crear_detalle(detalle: DetalleVenta, token: str = Depends(validar_token)):
#     #de ser necesario verificar si no existe otro igual antes de crear este nuevo (no valido para detallesVenta)

#     detalle_dict = dict(detalle)
#     del detalle_dict["id"] #quitar el id para que no se guarde como null
#     id = db_client.local.detalles_venta.insert_one(detalle_dict).inserted_id #mongodb crea automaticamente el id como "_id"

#     nuevo_detalle = detalle_venta_schema(db_client.local.detalles_venta.find_one({"_id":id})) #izquierda= que tiene que buscar. derecha= esto tiene que buscar

#     #await manager.broadcast(f"post-detalle:{str(id)}") #Notificar a todos

#     return DetalleVenta(**nuevo_detalle) #el ** sirve para pasar los valores del diccionario

# @router.put("/", response_model=DetalleVenta, status_code=status.HTTP_200_OK) #put
# async def actualizar_detalle(detalle: DetalleVenta, token: str = Depends(validar_token)):
#     print(detalle)
#     if not detalle.id:  # Validar si el id está presente
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, 
#             detail="El campo 'id' es obligatorio para actualizar un detalle de venta" #se necesita enviar mismo id si no no actualiza
#         )

#     detalle_dict = dict(detalle)
#     del detalle_dict["id"] #eliminar id para no actualizar el id
#     try:
#         db_client.local.detalles_venta.find_one_and_replace({"_id":ObjectId(detalle.id)}, detalle_dict)

#     except:        
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el detalle de venta (put)')
    
#     #await manager.broadcast(f"put-detalle:{str(ObjectId(detalle.id))}") #Notificar a todos

#     return search_detalle("_id", ObjectId(detalle.id))

# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
# async def detele_detalle(id: str, token: str = Depends(validar_token)):
#     found = db_client.local.detalles_venta.find_one_and_delete({"_id": ObjectId(id)})
#     if not found:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el detalle de venta')
#     else:
#         #await manager.broadcast(f"delete-detalle:{str(id)}") #Notificar a todos
#         return {'message':'Eliminado con exito'} 
    

# def search_detalle(field: str, key):
#     try:
#         detalle = db_client.local.detalles_venta.find_one({field: key})
#         if not detalle:  # Verificar si no se encontró el detalle
#             return None
#         return DetalleVenta(**detalle_venta_schema(detalle))  # el ** sirve para pasar los valores del diccionario
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar detalle: {str(e)}')

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pymongo import DESCENDING
from core.database import db_client
from generador_folio import generar_folio_cotizacion, obtener_nombre_sucursal
from models.cotizacion import Cotizacion
from schemas.cotizacion import cotizaciones_schema, cotizacion_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])

@router.get("/all", response_model=list[Cotizacion])
async def obtener_cotizaciones(token: str = Depends(validar_token)):
    cotizaciones = db_client.local.cotizaciones.find().sort("fecha_cotizacion", DESCENDING)
    return cotizaciones_schema(cotizaciones)

@router.get("/{id}") #path
async def obtener_cotizacion_path(id: str, token: str = Depends(validar_token)):
    return search_cotizaciones("_id", ObjectId(id))
    
@router.get("/") #Query
async def obtener_cotizacion_query(id: str, token: str = Depends(validar_token)):
    return search_cotizaciones("_id", ObjectId(id))

#TODO: obtener cotizaciones por sucursal


@router.post("/", response_model=Cotizacion, status_code=status.HTTP_201_CREATED) #post
async def crear_cotizacion(cotizacion: Cotizacion, token: str = Depends(validar_token)):
    cotizacion_dict = cotizacion.model_dump()

    #generacion de folio
    cotizacion_dict["folio"] = generar_folio_cotizacion(db_client.local)

    cotizacion_dict["detalles"] = [d.model_dump() for d in cotizacion.detalles]
    del cotizacion_dict["id"] #quitar el id para que no se guarde como null
    cotizacion_dict["subtotal"] = Decimal128(cotizacion_dict["subtotal"])
    cotizacion_dict["descuento"] = Decimal128(cotizacion_dict["descuento"])
    cotizacion_dict["iva"] = Decimal128(cotizacion_dict["iva"])
    cotizacion_dict["total"] = Decimal128(cotizacion_dict["total"])
    

    for detalle in cotizacion_dict["detalles"]:
        detalle["_id"] = ObjectId()
        detalle["descuento_aplicado"] = Decimal128(detalle["descuento_aplicado"])
        detalle["iva"] = Decimal128(detalle["iva"])
        detalle["subtotal"] = Decimal128(detalle["subtotal"])
        detalle["cotizacion_precio"] = Decimal128(detalle["cotizacion_precio"])
        detalle.pop("id", None)  # ✅ eliminar el duplicado

    id = db_client.local.cotizaciones.insert_one(cotizacion_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_cotizacion = cotizacion_schema(db_client.local.cotizaciones.find_one({"_id":id}))
    
    await manager.broadcast(f"post-cotizacion:{str(id)}")
    return Cotizacion(**nueva_cotizacion)


def search_cotizaciones(field: str, key):
    try:
        cotizacion = db_client.local.cotizaciones.find_one({field: key})
        if not cotizacion:  # Verificar si no se encontró la cotizacion
            return None
        return Cotizacion(**cotizacion_schema(cotizacion))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la cotizacion: {str(e)}')


# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
# async def detele_venta(id: str, token: str = Depends(validar_token)):
#     found = db_client.local.ventas.find_one_and_delete({"_id": ObjectId(id)})
#     if not found:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la venta')
#     else:
#         await manager.broadcast(f"delete-venta:{str(id)}") #Notificar a todos
#         return {'message':'Eliminada con exito'} 
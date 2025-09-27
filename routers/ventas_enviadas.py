from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from core.database import db_client
from models.venta_enviada import VentaEnviada
from schemas.venta_enviada import ventas_enviadas_schema, venta_enviada_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/ventas_enviadas", tags=["ventas_enviadas"])

@router.get("/all", response_model=list[VentaEnviada])
async def obtener_ventas(token: str = Depends(validar_token)):
    return ventas_enviadas_schema(db_client.local.ventas_enviadas.find())

@router.get("/{id}") #path
async def obtener_venta_path(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))
    
@router.get("/") #Query
async def obtener_venta_query(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))

@router.post("/", response_model=VentaEnviada, status_code=status.HTTP_201_CREATED) #post
async def crear_venta(venta: VentaEnviada, token: str = Depends(validar_token)):
    venta_dict = venta.model_dump()

    #generacion de folio
    venta_dict["detalles"] = [d.model_dump() for d in venta.detalles]
    del venta_dict["id"] #quitar el id para que no se guarde como null
    venta_dict["subtotal"] = Decimal128(venta_dict["subtotal"])
    venta_dict["descuento"] = Decimal128(venta_dict["descuento"])
    venta_dict["iva"] = Decimal128(venta_dict["iva"])
    venta_dict["total"] = Decimal128(venta_dict["total"])
    

    for detalle in venta_dict["detalles"]:
        detalle["_id"] = ObjectId()
        detalle["descuento_aplicado"] = Decimal128(detalle["descuento_aplicado"])
        detalle["iva"] = Decimal128(detalle["iva"])
        detalle["subtotal"] = Decimal128(detalle["subtotal"])
        detalle.pop("id", None)  # ✅ eliminar el duplicado

    id = db_client.local.ventas_enviadas.insert_one(venta_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_venta = venta_enviada_schema(db_client.local.ventas_enviadas.find_one({"_id":id}))
    
    await manager.broadcast(f"ventaenviada:{str(venta_dict["sucursal_id"])}")
    return VentaEnviada(**nueva_venta)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
async def detele_venta(id: str, sucursal: str, token: str = Depends(validar_token)):
     found = db_client.local.ventas_enviadas.find_one_and_delete({"_id": ObjectId(id)})
     if not found:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la venta')
     else:
         await manager.broadcast(f"ventaenviada:{sucursal}") #Notificar a todos
         return {'message':'Eliminada con exito'} 
     
def search_venta(field: str, key):
    try:
        venta = db_client.local.ventas_enviadas.find_one({field: key})
        if not venta:  # Verificar si no se encontró la venta
            raise HTTPException(status_code=404, detail="Venta enviada no encontrada")
        return VentaEnviada(**venta_enviada_schema(venta))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la venta: {str(e)}')

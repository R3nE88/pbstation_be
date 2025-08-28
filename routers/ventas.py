from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from core.database import db_client
from generador_folio import generar_folio_venta, obtener_nombre_sucursal
from models.venta import Venta
from schemas.venta import ventas_schema, venta_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/ventas", tags=["ventas"])

@router.get("/all", response_model=list[Venta])
async def obtener_ventas(token: str = Depends(validar_token)):
    return ventas_schema(db_client.local.ventas.find())


@router.get("/caja/{caja_id}", response_model=list[Venta])
async def obtener_ventas_por_caja(caja_id: str, token: str = Depends(validar_token)):
    try:
        ventas = db_client.local.ventas.find({"caja_id": caja_id})
        ventas_list = ventas_schema(ventas)  # Convertir los resultados a un esquema de lista
        return ventas_list  # Puede ser [] y no es error
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas: {str(e)}"
        )



@router.get("/{id}") #path
async def obtener_venta_path(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))
    
@router.get("/") #Query
async def obtener_venta_query(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))


@router.post("/", response_model=Venta, status_code=status.HTTP_201_CREATED) #post
async def crear_venta(venta: Venta, token: str = Depends(validar_token)):
    venta_dict = venta.model_dump()

    #generacion de folio
    nombre_sucursal = obtener_nombre_sucursal(db_client.local, venta.sucursal_id)
    venta_dict["folio"] = generar_folio_venta(db_client.local, nombre_sucursal)

    venta_dict["detalles"] = [d.model_dump() for d in venta.detalles]
    del venta_dict["id"] #quitar el id para que no se guarde como null
    venta_dict["subtotal"] = Decimal128(venta_dict["subtotal"])
    venta_dict["descuento"] = Decimal128(venta_dict["descuento"])
    venta_dict["iva"] = Decimal128(venta_dict["iva"])
    venta_dict["total"] = Decimal128(venta_dict["total"])
    venta_dict["recibido_efect"] = Decimal128(venta_dict["recibido_efect"]) if venta_dict.get("recibido_efect") is not None else None
    venta_dict["recibido_tarj"] = Decimal128(venta_dict["recibido_tarj"]) if venta_dict.get("recibido_tarj") is not None else None
    venta_dict["recibido_trans"] = Decimal128(venta_dict["recibido_trans"]) if venta_dict.get("recibido_trans") is not None else None
    venta_dict["recibido_total"] = Decimal128(venta_dict["recibido_total"]) if venta_dict.get("recibido_total") is not None else None
    venta_dict["abonado"] = Decimal128(venta_dict["abonado"]) if venta_dict.get("abonado") is not None else None
    venta_dict["cambio"] = Decimal128(venta_dict["cambio"]) if venta_dict.get("cambio") is not None else None
    

    for detalle in venta_dict["detalles"]:
        detalle["_id"] = ObjectId()
        detalle["descuento_aplicado"] = Decimal128(detalle["descuento_aplicado"])
        detalle["iva"] = Decimal128(detalle["iva"])
        detalle["subtotal"] = Decimal128(detalle["subtotal"])
        detalle.pop("id", None)  # ✅ eliminar el duplicado

    id = db_client.local.ventas.insert_one(venta_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_venta = venta_schema(db_client.local.ventas.find_one({"_id":id}))
    
    await manager.broadcast(f"post-venta:{str(id)}")
    return Venta(**nueva_venta)


def search_venta(field: str, key):
    try:
        venta = db_client.local.ventas.find_one({field: key})
        if not venta:  # Verificar si no se encontró la venta
            return None
        return Venta(**venta_schema(venta))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la venta: {str(e)}')


# @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT) #delete path
# async def detele_venta(id: str, token: str = Depends(validar_token)):
#     found = db_client.local.ventas.find_one_and_delete({"_id": ObjectId(id)})
#     if not found:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la venta')
#     else:
#         await manager.broadcast(f"delete-venta:{str(id)}") #Notificar a todos
#         return {'message':'Eliminada con exito'} 
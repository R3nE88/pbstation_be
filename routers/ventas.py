from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header, status, Depends
from dotenv import load_dotenv
import os
from core.database import db_client
from models.venta import Venta
from schemas.venta import ventas_schema, venta_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
import re
from datetime import datetime

# Cargar variables de entorno desde config.env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.env")
load_dotenv(dotenv_path=dotenv_path)

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY = SECRET_KEY.strip()  # Eliminar espacios o saltos de línea

router = APIRouter(prefix="/ventas", tags=["ventas"])

def validar_token(tkn: str = Header(None, description="El token de autorización es obligatorio")):
    if tkn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sin Authorizacion"
        )
    if tkn != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorizacion inválida"
        )
    

#para obtener el folio de la venta
def abreviar_sucursal(nombre: str) -> str:
    match = re.search(r'(\d+\w*)', nombre)
    if match:
        return f"S{match.group(1)}"
    return "S0"

def obtener_consecutivo(db, sucursal_abreviada: str, fecha: str) -> int:
    pattern = f"^{sucursal_abreviada}-{fecha}-"
    folios_hoy = db.ventas.count_documents({"folio": {"$regex": pattern}})
    return folios_hoy + 1

def generar_folio(db, nombre_sucursal: str) -> str:
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    fecha = datetime.now().strftime("%y%m%d")
    consecutivo = obtener_consecutivo(db, sucursal_abreviada, fecha)
    return f"{sucursal_abreviada}-{fecha}-{consecutivo:05d}"

def obtener_nombre_sucursal(db, sucursal_id_str: str) -> str:
    try:
        sucursal_id = ObjectId(sucursal_id_str)
    except:
        raise HTTPException(status_code=400, detail="ID de sucursal inválido")

    sucursal = db.sucursales.find_one({"_id": sucursal_id})
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return sucursal["nombre"]
# aqui termina la funcion para generar el folio


@router.get("/all", response_model=list[Venta])
async def obtener_ventas(token: str = Depends(validar_token)):
    return ventas_schema(db_client.local.ventas.find())

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
    venta_dict["folio"] = generar_folio(db_client.local, nombre_sucursal)

    venta_dict["detalles"] = [d.model_dump() for d in venta.detalles]
    del venta_dict["id"] #quitar el id para que no se guarde como null
    venta_dict["subtotal"] = Decimal128(venta_dict["subtotal"])
    venta_dict["descuento"] = Decimal128(venta_dict["descuento"])
    venta_dict["iva"] = Decimal128(venta_dict["iva"])
    venta_dict["total"] = Decimal128(venta_dict["total"])
    venta_dict["recibido"] = Decimal128(venta_dict["recibido"])
    venta_dict["abonado"] = Decimal128(venta_dict["abonado"])
    venta_dict["cambio"] = Decimal128(venta_dict["cambio"])
    

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
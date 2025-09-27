
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pymongo import ASCENDING, DESCENDING
from core.database import db_client
from generador_folio import generar_folio_venta
from models.venta import Venta
from schemas.venta import venta_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/ventas", tags=["ventas"])

@router.get("/caja/{caja_id}", response_model=list[Venta])
async def obtener_ventas_de_caja(caja_id: str, token: str = Depends(validar_token), orden: str = "asc"): #asc o desc
    try:
        try:
            caja = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="caja_id inválido")
        if not caja:
            raise HTTPException(status_code=404, detail="Caja no encontrada")

        cortes_ids = caja.get("cortes_ids", [])
        if not cortes_ids:
            return []

        def to_oid(x):
            return x if isinstance(x, ObjectId) else ObjectId(str(x))

        cortes_oids = [to_oid(c) for c in cortes_ids]

        cortes_cursor = db_client.local.cortes.find(
            {"_id": {"$in": cortes_oids}},
            {"ventas_ids": 1}  # proyecta solo lo necesario
        )
        cortes = {c["_id"]: c for c in cortes_cursor}  # map por id

        ventas_ids_flat = []
        for corte_id in cortes_oids:
            corte = cortes.get(corte_id)
            if not corte:
                continue
            ventas_ids_flat.extend(corte.get("ventas_ids", []))

        if not ventas_ids_flat:
            return []

        ventas_oids = list({to_oid(v) for v in ventas_ids_flat})

        ventas_cursor = db_client.local.ventas.find(
            {"_id": {"$in": ventas_oids}}
        )
        ventas = list(ventas_cursor)

        #Ordenar por fecha. Probar campos comunes; si no existe, usar timestamp del ObjectId
        date_fields = ["fecha", "fecha_venta", "fecha_cotizacion", "created_at"]
        def venta_date(v):
            for f in date_fields:
                if f in v and v[f]:
                    return v[f]
            # fallback: usar el timestamp del ObjectId (generación)
            _id = v.get("_id")
            if isinstance(_id, ObjectId):
                return _id.generation_time
            return None

        reverse = (orden.lower() != "asc") 
        ventas_sorted = sorted(ventas, key=lambda v: venta_date(v) or 0, reverse=reverse)

        return [venta_schema(v) for v in ventas_sorted]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas de la caja: {str(e)}"
        )

@router.get("/corte/{corte_id}", response_model=list[Venta])
async def obtener_ventas_de_corte(
    corte_id: str,
    token: str = Depends(validar_token),
    orden: str = "asc"             # "asc" o "desc"
):
    try:
        # validar corte_id
        try:
            corte_oid = ObjectId(corte_id)
        except Exception:
            raise HTTPException(status_code=400, detail="corte_id inválido")

        # traer solo ventas_ids (proyección)
        corte = db_client.local.cortes.find_one({"_id": corte_oid}, {"ventas_ids": 1})
        if not corte:
            raise HTTPException(status_code=404, detail="Corte no encontrado")

        ventas_ids_raw = corte.get("ventas_ids", [])
        if not ventas_ids_raw:
            return []

        # helpers para normalizar ObjectId / string y obtener claves
        def to_oid(x):
            return x if isinstance(x, ObjectId) else ObjectId(str(x))

        def oid_hex(x):
            return str(to_oid(x))

        # normalizar lista de ObjectId para la consulta
        ventas_oids = [to_oid(v) for v in ventas_ids_raw]

        # traer todas las ventas con una sola consulta
        # proyecta solo campos necesarios si quieres: e.g. {"field1":1, "field2":1}
        ventas_cursor = db_client.local.ventas.find({"_id": {"$in": ventas_oids}})
        ventas_list = list(ventas_cursor)

        # mapa por _id hex para reconstruir el orden original
        ventas_map = {str(v["_id"]): v for v in ventas_list}

        # reconstruir respetando el orden de ventas_ids en el corte
        ventas_ordenadas = []
        for v_raw in ventas_ids_raw:
            k = oid_hex(v_raw)
            v = ventas_map.get(k)
            if v:
                ventas_ordenadas.append(venta_schema(v))
            # si no existe la venta (borrada/inconsistente) la ignoramos

        return ventas_ordenadas

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas del corte: {str(e)}"
        )
    
@router.get("/{id}") #path
async def obtener_venta_path(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))
    
@router.get("/") #Query
async def obtener_venta_query(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))

@router.post("/por-id", response_model=list[Venta])
async def obtener_ventas_por_ids(
    ventas_ids: list[str],
    sucursal_id: str = None,
    token: str = Depends(validar_token),
    orden: str = "asc"
):
    if not ventas_ids:
        return []
    try:
        ventas_oids = [ObjectId(venta_id) for venta_id in ventas_ids]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más IDs de venta tienen formato inválido"
        )
    query_filter = {"_id": {"$in": ventas_oids}}
    if sucursal_id:
        query_filter["sucursal_id"] = sucursal_id
    try:
        ventas_list = list(db_client.local.ventas.find(query_filter))
        if not ventas_list:
            return []
        def get_fecha_venta(venta):
            return venta.get("fecha_venta") or venta["_id"].generation_time
        reverse = orden.lower() == "desc"
        ventas_sorted = sorted(ventas_list, key=get_fecha_venta, reverse=reverse)
        return [venta_schema(v) for v in ventas_sorted]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas por IDs: {str(e)}"
        )

@router.post("/{corte_id}", response_model=Venta, status_code=status.HTTP_201_CREATED) #post
async def crear_venta(venta: Venta, corte_id:str, is_deuda:bool,  token: str = Depends(validar_token)):
    venta_dict = venta.model_dump()

    #generacion de folio
    if not venta_dict.get("folio"):
        venta_dict["folio"] = generar_folio_venta(db_client.local, venta.sucursal_id)

    venta_dict["detalles"] = [d.model_dump() for d in venta.detalles]
    del venta_dict["id"] #quitar el id para que no se guarde como null
    venta_dict["subtotal"] = Decimal128(venta_dict["subtotal"])
    venta_dict["descuento"] = Decimal128(venta_dict["descuento"])
    venta_dict["iva"] = Decimal128(venta_dict["iva"])
    venta_dict["total"] = Decimal128(venta_dict["total"])
    venta_dict["recibido_mxn"] = Decimal128(venta_dict["recibido_mxn"]) if venta_dict.get("recibido_mxn") is not None else None
    venta_dict["recibido_us"] = Decimal128(venta_dict["recibido_us"]) if venta_dict.get("recibido_us") is not None else None
    venta_dict["recibido_tarj"] = Decimal128(venta_dict["recibido_tarj"]) if venta_dict.get("recibido_tarj") is not None else None
    venta_dict["recibido_trans"] = Decimal128(venta_dict["recibido_trans"]) if venta_dict.get("recibido_trans") is not None else None
    venta_dict["recibido_total"] = Decimal128(venta_dict["recibido_total"])
    venta_dict["abonado_mxn"] = Decimal128(venta_dict["abonado_mxn"]) if venta_dict.get("abonado_mxn") is not None else None
    venta_dict["abonado_us"] = Decimal128(venta_dict["abonado_us"]) if venta_dict.get("abonado_us") is not None else None
    venta_dict["abonado_tarj"] = Decimal128(venta_dict["abonado_tarj"]) if venta_dict.get("abonado_tarj") is not None else None
    venta_dict["abonado_trans"] = Decimal128(venta_dict["abonado_trans"]) if venta_dict.get("abonado_trans") is not None else None
    venta_dict["abonado_total"] = Decimal128(venta_dict["abonado_total"]) if venta_dict.get("abonado_total") is not None else None
    venta_dict["cambio"] = Decimal128(venta_dict["cambio"]) if venta_dict.get("cambio") is not None else None

    for detalle in venta_dict["detalles"]:
        detalle["descuento_aplicado"] = Decimal128(detalle["descuento_aplicado"])
        detalle["iva"] = Decimal128(detalle["iva"])
        detalle["subtotal"] = Decimal128(detalle["subtotal"])
        

    id = db_client.local.ventas.insert_one(venta_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_venta = venta_schema(db_client.local.ventas.find_one({"_id":id}))

    # Actualizar el corte agregando el id de la nueva venta a ventas_ids
    db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$push": {"ventas_ids": str(id)}}
    )

    if is_deuda:
        await manager.broadcast(f"delete-venta-deuda:{str(ObjectId(venta.id))}")

    return Venta(**nueva_venta)

@router.patch("/{venta_id}/marcar-deuda", response_model=Venta, status_code=status.HTTP_200_OK)
async def marcar_deuda_pagada(venta_id: str, token: str = Depends(validar_token)):
    try:
        venta_oid = ObjectId(venta_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de venta inválido")
    
    try:
        # Actualizar la venta
        db_client.local.ventas.update_one(
            {"_id": venta_oid},
            {"$set": {"liquidado": True}}
        )
        
        # Obtener y retornar la venta actualizada
        venta_actualizada = db_client.local.ventas.find_one({"_id": venta_oid})
        
        if not venta_actualizada:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        return Venta(**venta_schema(venta_actualizada))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar la venta: {str(e)}"
        )

def search_venta(field: str, key):
    try:
        venta = db_client.local.ventas.find_one({field: key})
        if not venta:  # Verificar si no se encontró la venta
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        return Venta(**venta_schema(venta))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la venta: {str(e)}')
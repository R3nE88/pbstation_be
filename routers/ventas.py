from decimal import Decimal
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pymongo import ASCENDING, DESCENDING
from core.database import db_client
from generador_folio import generar_folio_venta, obtener_nombre_sucursal
from models.venta import Venta
from schemas.venta import ventas_schema, venta_schema
from routers.websocket import manager
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/ventas", tags=["ventas"])

# @router.get("/all", response_model=list[Venta])
# async def obtener_ventas(token: str = Depends(validar_token)):
#     return ventas_schema(db_client.local.ventas.find())


@router.get("/caja/{caja_id}", response_model=list[Venta])
async def obtener_ventas_de_caja(caja_id: str, token: str = Depends(validar_token), orden: str = "asc"): #asc o desc
    try:
        # 1) Obtener caja
        try:
            caja = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="caja_id inválido")
        if not caja:
            raise HTTPException(status_code=404, detail="Caja no encontrada")

        cortes_ids = caja.get("cortes_ids", [])
        if not cortes_ids:
            return []

        # helper: asegurar ObjectId
        def to_oid(x):
            return x if isinstance(x, ObjectId) else ObjectId(str(x))

        cortes_oids = [to_oid(c) for c in cortes_ids]

        # 2) Traer cortes (una sola consulta)
        cortes_cursor = db_client.local.cortes.find(
            {"_id": {"$in": cortes_oids}},
            {"ventas_ids": 1}  # proyecta solo lo necesario
        )
        cortes = {c["_id"]: c for c in cortes_cursor}  # map por id

        # 3) Recolectar ventas_ids en el orden lógico (si quieres mantener orden por corte)
        ventas_ids_flat = []
        for corte_id in cortes_oids:
            corte = cortes.get(corte_id)
            if not corte:
                continue
            ventas_ids_flat.extend(corte.get("ventas_ids", []))

        if not ventas_ids_flat:
            return []

        # eliminar duplicados pero conservar (opcional) -> aquí eliminamos duplicados para optimizar
        ventas_oids = list({to_oid(v) for v in ventas_ids_flat})

        # 4) Traer todas las ventas en una sola consulta
        ventas_cursor = db_client.local.ventas.find(
            {"_id": {"$in": ventas_oids}}
        )
        ventas = list(ventas_cursor)

        # 5) Ordenar por fecha. Probar campos comunes; si no existe, usar timestamp del ObjectId
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

        # 6) Mapear a tu schema/serializador
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
    orden_por: str | None = None,   # e.g. "fecha" -> opcional, si se setea ignora el orden en ventas_ids
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

        if orden_por:  # ordenar por campo específico en lugar del orden en ventas_ids
            reverse = (orden.lower() != "asc")
            # proteger si campo no existe en algunas ventas -> usar None al final
            def key_fn(v):
                val = v.get(orden_por)
                # si es None, pondremos un valor por debajo/encima según reverse
                return (val is None, val)
            ventas_sorted = sorted(ventas_list, key=key_fn, reverse=reverse)
            return [venta_schema(v) for v in ventas_sorted]

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
    

# @router.get("/corte/{corte_id}/por-producto")
# async def obtener_ventas_por_producto(corte_id: str, token: str = Depends(validar_token)):
#     try:
#         corte = db_client.local.cortes.find_one({"_id": ObjectId(corte_id)})
#         if not corte:
#             raise HTTPException(status_code=404, detail="Corte no encontrado")
#         ventas_ids = corte.get("ventas_ids", [])
#         resumen: dict[str, dict] = {}

#         for venta_id in ventas_ids:
#             venta = db_client.local.ventas.find_one({"_id": ObjectId(venta_id)})
#             if not venta:
#                 continue
#             for detalle in venta.get("detalles", []):
#                 producto_id = detalle["producto_id"]

#                 if producto_id not in resumen:
#                     resumen[producto_id] = {
#                         "producto_id": producto_id,
#                         "cantidad": 0,
#                         "subtotal": Decimal("0.00"),
#                         "iva": Decimal("0.00"),
#                         "total": Decimal("0.00"),
#                     }

#                 cantidad = detalle.get("cantidad", 0)
#                 subtotal = Decimal(str(detalle.get("subtotal", Decimal128("0")).to_decimal()))
#                 iva = Decimal(str(detalle.get("iva", Decimal128("0")).to_decimal()))

#                 resumen[producto_id]["cantidad"] += cantidad
#                 resumen[producto_id]["subtotal"] += subtotal - iva
#                 resumen[producto_id]["iva"] += iva
#                 resumen[producto_id]["total"] += subtotal

#         return list(resumen.values())

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al obtener las ventas por producto: {str(e)}"
#         )


@router.get("/{id}") #path
async def obtener_venta_path(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))
    

@router.get("/") #Query
async def obtener_venta_query(id: str, token: str = Depends(validar_token)):
    return search_venta("_id", ObjectId(id))


@router.post("/{corte_id}", response_model=Venta, status_code=status.HTTP_201_CREATED) #post
async def crear_venta(venta: Venta, corte_id:str,  token: str = Depends(validar_token)):
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
    venta_dict["recibido_mxn"] = Decimal128(venta_dict["recibido_mxn"]) if venta_dict.get("recibido_mxn") is not None else None
    venta_dict["recibido_us"] = Decimal128(venta_dict["recibido_us"]) if venta_dict.get("recibido_us") is not None else None
    venta_dict["recibido_tarj"] = Decimal128(venta_dict["recibido_tarj"]) if venta_dict.get("recibido_tarj") is not None else None
    venta_dict["recibido_trans"] = Decimal128(venta_dict["recibido_trans"]) if venta_dict.get("recibido_trans") is not None else None
    venta_dict["abonado_mxn"] = Decimal128(venta_dict["abonado_mxn"]) if venta_dict.get("abonado_mxn") is not None else None
    venta_dict["abonado_us"] = Decimal128(venta_dict["abonado_us"]) if venta_dict.get("abonado_us") is not None else None
    venta_dict["abonado_tarj"] = Decimal128(venta_dict["abonado_tarj"]) if venta_dict.get("abonado_tarj") is not None else None
    venta_dict["abonado_trans"] = Decimal128(venta_dict["abonado_trans"]) if venta_dict.get("abonado_trans") is not None else None
    venta_dict["abonado_total"] = Decimal128(venta_dict["abonado_total"]) if venta_dict.get("abonado_total") is not None else None
    venta_dict["cambio"] = Decimal128(venta_dict["cambio"]) if venta_dict.get("cambio") is not None else None
    

    for detalle in venta_dict["detalles"]:
        detalle["_id"] = ObjectId()
        detalle["descuento_aplicado"] = Decimal128(detalle["descuento_aplicado"])
        detalle["iva"] = Decimal128(detalle["iva"])
        detalle["subtotal"] = Decimal128(detalle["subtotal"])
        detalle.pop("id", None)  # ✅ eliminar el duplicado

    id = db_client.local.ventas.insert_one(venta_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_venta = venta_schema(db_client.local.ventas.find_one({"_id":id}))

    # Actualizar el corte agregando el id de la nueva venta a ventas_ids
    db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$push": {"ventas_ids": str(id)}}
    )
    
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
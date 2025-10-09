
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Header, status, Depends
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
async def obtener_ventas_de_caja(caja_id: str, token: str = Depends(validar_token), orden: str = "asc"):
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
            {"ventas_ids": 1}
        )
        cortes = {c["_id"]: c for c in cortes_cursor}
        ventas_ids_flat = []
        for corte_id in cortes_oids:
            corte = cortes.get(corte_id)
            if not corte:
                continue
            ventas_ids_flat.extend(corte.get("ventas_ids", []))
        if not ventas_ids_flat:
            return []

        ventas_oids = list({to_oid(v) for v in ventas_ids_flat})
        ventas_cursor = db_client.local.ventas.find({"_id": {"$in": ventas_oids}})
        ventas = list(ventas_cursor)
        reverse = (orden.lower() != "asc") 
        ventas_sorted = sorted(ventas, key=lambda v: v.get("fecha_venta") or v["_id"].generation_time, reverse=reverse)

        return [venta_schema(v) for v in ventas_sorted]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas de la caja: {str(e)}"
        )

@router.get("/corte/{corte_id}", response_model=list[Venta])
async def obtener_ventas_de_corte(corte_id: str, token: str = Depends(validar_token), orden: str = "asc"):
    try:
        try:
            corte_oid = ObjectId(corte_id)
        except Exception:
            raise HTTPException(status_code=400, detail="corte_id inválido")

        corte = db_client.local.cortes.find_one({"_id": corte_oid}, {"ventas_ids": 1})
        if not corte:
            raise HTTPException(status_code=404, detail="Corte no encontrado")

        ventas_ids_raw = corte.get("ventas_ids", [])
        if not ventas_ids_raw:
            return []

        def to_oid(x):
            return x if isinstance(x, ObjectId) else ObjectId(str(x))

        ventas_oids = [to_oid(v) for v in ventas_ids_raw]
        ventas_cursor = db_client.local.ventas.find({"_id": {"$in": ventas_oids}})
        ventas_map = {str(v["_id"]): v for v in ventas_cursor}
        ventas_ordenadas = []
        for v_raw in ventas_ids_raw:
            v = ventas_map.get(str(to_oid(v_raw)))
            if v:
                ventas_ordenadas.append(venta_schema(v))

        return ventas_ordenadas

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las ventas del corte: {str(e)}"
        )
    
@router.get("/{id}")
async def obtener_venta(id: str, token: str = Depends(validar_token)):
    try:
        venta = search_venta("_id", ObjectId(id))
        if venta is None:
            raise HTTPException(status_code=404, detail="VentaEnviada no encontrada")
        return venta
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
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
async def pagar_venta(venta: Venta, corte_id:str, is_deuda:bool,  token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
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
    db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$push": {"ventas_ids": str(id)}}
    )
    if is_deuda: # si es deuda, notificar a los demas
        await manager.broadcast(
            f"delete-venta-deuda:{str(ObjectId(venta.id))}",
            exclude_connection_id=x_connection_id
        )
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

@router.patch("/{venta_id}/cancelar", response_model=Venta, status_code=status.HTTP_200_OK)
async def cancelar_venta(
    venta_id: str, 
    motivo_cancelacion: str,
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    try:
        venta_oid = ObjectId(venta_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de venta inválido")
    
    # Validar que el motivo no esté vacío
    if not motivo_cancelacion or motivo_cancelacion.strip() == "":
        raise HTTPException(status_code=400, detail="El motivo de cancelación es requerido")
    
    try:
        # Verificar que la venta existe
        venta_existente = db_client.local.ventas.find_one({"_id": venta_oid})
        if not venta_existente:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        # Verificar si la venta ya está cancelada
        if venta_existente.get("cancelado", False):
            raise HTTPException(status_code=400, detail="La venta ya está cancelada")
        
        # Preparar los campos a actualizar
        update_fields = {
            "cancelado": True,
            "motivo_cancelacion": motivo_cancelacion.strip(),
            "recibido_mxn": Decimal128("0"),
            "recibido_us": Decimal128("0"),
            "recibido_tarj": Decimal128("0"),
            "recibido_trans": Decimal128("0"),
            "recibido_total": Decimal128("0"),
            "abonado_mxn": Decimal128("0"),
            "abonado_us": Decimal128("0"),
            "abonado_tarj": Decimal128("0"),
            "abonado_trans": Decimal128("0"),
            "abonado_total": Decimal128("0"),
            "cambio": Decimal128("0")
        }
        
        # Si la venta no está liquidada, marcarla como liquidada y eliminar el adeudo del cliente
        if not venta_existente.get("liquidado", False):
            update_fields["liquidado"] = True
            update_fields["was_deuda"] = False
            
            # Obtener el cliente_id de la venta
            cliente_id = venta_existente.get("cliente_id")
            
            if cliente_id:
                # Convertir a ObjectId si es necesario
                try:
                    cliente_oid = ObjectId(cliente_id) if not isinstance(cliente_id, ObjectId) else cliente_id
                    
                    # Verificar que el cliente existe
                    cliente_existente = db_client.local.clientes.find_one({"_id": cliente_oid})
                    if cliente_existente:
                        # Eliminar el adeudo del cliente usando $pull
                        result = db_client.local.clientes.update_one(
                            {"_id": cliente_oid},
                            {"$pull": {"adeudos": {"venta_id": str(venta_oid)}}}
                        )
                        
                        # Si se eliminó el adeudo, notificar por WebSocket
                        if result.modified_count > 0:
                            await manager.broadcast(
                                f"put-cliente:{str(cliente_oid)}",
                                exclude_connection_id=x_connection_id
                            )
                except Exception as e:
                    # Si hay error al procesar el cliente, continuar con la cancelación de la venta
                    print(f"Advertencia: No se pudo eliminar el adeudo del cliente: {str(e)}")
        
        # Actualizar la venta
        db_client.local.ventas.update_one(
            {"_id": venta_oid},
            {"$set": update_fields}
        )
        
        # Obtener y retornar la venta actualizada
        venta_actualizada = db_client.local.ventas.find_one({"_id": venta_oid})
        
        # Notificar por WebSocket la actualización de la venta
        await manager.broadcast(
            f"put-venta:{str(venta_oid)}",
            exclude_connection_id=x_connection_id
        )
        
        return Venta(**venta_schema(venta_actualizada))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar la venta: {str(e)}"
        )

def search_venta(field: str, key):
    try:
        venta = db_client.local.ventas.find_one({field: key})
        if not venta:  # Verificar si no se encontró la venta
            return None
        return Venta(**venta_schema(venta))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la venta: {str(e)}')
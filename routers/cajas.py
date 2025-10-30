from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Response, status, Depends, Body
from core.database import db_client
from generador_folio import generar_folio_caja, generar_folio_corte
from models.caja import Caja
from models.corte import Corte
from schemas.caja import cajas_schema, caja_schema
from schemas.corte import cortes_schema, corte_schema
from schemas.movimiento_caja import movimiento_caja_schema, movimiento_cajas_schema
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/cajas", tags=["cajas"])

# ----------------------------------------  CAJA  ----------------------------------------
@router.get("/all")
async def obtener_cajas(
    page: int = 1,
    page_size: int = 60,
    sucursal_id: str = None,
    token: str = Depends(validar_token)
):
    filtros = {"estado": "cerrada"}  
    if sucursal_id:
        filtros["sucursal_id"] = sucursal_id
    total = db_client.local.cajas.count_documents(filtros)
    skip = (page - 1) * page_size
    cajas = db_client.local.cajas.find(filtros)\
        .sort("fecha_apertura", -1)\
        .skip(skip)\
        .limit(page_size)
    total_pages = (total + page_size - 1) // page_size
    return {
        "data": cajas_schema(cajas),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@router.get("/{id}")
async def obtener_caja(id: str, token: str = Depends(validar_token)):
    try:
        caja = search_caja("_id", ObjectId(id))
        if caja is None:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        return caja
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")

@router.post("/", response_model=Caja, status_code=status.HTTP_201_CREATED) #post
async def crear_caja(caja: Caja, token: str = Depends(validar_token)):
    caja_dict = caja.model_dump()

    #generacion de folio
    caja_dict["folio"] = generar_folio_caja(db_client.local)

    del caja_dict["id"] #quitar el id para que no se guarde como null
    caja_dict["venta_total"] = Decimal128(str(caja_dict["venta_total"])) if caja_dict["venta_total"] is not None else None
    caja_dict["cortes_ids"] = []

    id = db_client.local.cajas.insert_one(caja_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_caja = caja_schema(db_client.local.cajas.find_one({"_id":id}))
    
    return Caja(**nueva_caja)

@router.put("/", response_model=Caja, status_code=status.HTTP_200_OK) #put
async def actualizar_caja(caja: Caja, token: str = Depends(validar_token)):
    print(caja)
    if not caja.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar caja" #se necesita enviar mismo id si no no actualiza
        )
    caja_dict = caja.model_dump()
    del caja_dict["id"]
    caja_dict["venta_total"] = Decimal128(str(caja.venta_total)) if caja.venta_total is not None else None
    # Asegurar que cortes_ids se guarden como ObjectId en la BD
    if "cortes_ids" in caja_dict and caja_dict["cortes_ids"] is not None:
        try:
            caja_dict["cortes_ids"] = [ObjectId(cid) if isinstance(cid, str) else cid for cid in caja_dict["cortes_ids"]]
        except InvalidId:
            raise HTTPException(status_code=400, detail="Uno o más cortes_ids tienen formato inválido")
    try:
        result = db_client.local.cajas.find_one_and_replace(
            {"_id": ObjectId(caja.id)}, 
            caja_dict
        )
        if not result:
            raise HTTPException(status_code=404, detail='Caja no encontrada')
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    return Response(status_code=204)#search_caja("_id", ObjectId(caja.id))

def search_caja(field: str, key):
    try:
        caja = db_client.local.cajas.find_one({field: key})
        if not caja:  
            return None
        return Caja(**caja_schema(caja))
    except HTTPException:
        raise  # Re-lanzar HTTPException
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la caja: {str(e)}')

# ---------------------------------------- CORTES ----------------------------------------
@router.get("/{caja_id}/cortes/all", response_model=list[Corte])
async def obtener_all_cortes(caja_id: str, token: str = Depends(validar_token)):
    try:
        caja = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
        if not caja:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        
        cortes_ids = caja.get("cortes_ids", [])
        if not cortes_ids:
            return []
        
        # Asegurar que sean ObjectId
        cortes_ids_obj = [ObjectId(id) if isinstance(id, str) else id for id in cortes_ids]
        
        cortes_cursor = db_client.local.cortes.find(
            {"_id": {"$in": cortes_ids_obj}}
        ).sort("fecha_apertura", -1)
        
        cortes_list = list(cortes_cursor)
        return cortes_schema(cortes_list)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los cortes: {str(e)}"
        )
    
@router.get("/{caja_id}/cortes/ultimo", response_model=Corte)
async def obtener_ultimo_corte(caja_id: str, token: str = Depends(validar_token)):
    try:
        caja = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
        if not caja:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        cortes_ids = caja.get("cortes_ids", [])
        if not cortes_ids:
            raise HTTPException(status_code=404, detail="La caja no tiene cortes registrados")
        ultimo_corte = db_client.local.cortes.find_one(
            {"_id": {"$in": cortes_ids}},
            sort=[("fecha_apertura", -1)]
        )
        if not ultimo_corte:
            raise HTTPException(status_code=404, detail="Corte no encontrado")
        return Corte(**corte_schema(ultimo_corte))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el último corte: {str(e)}"
        )

@router.post("/{caja_id}/cortes", response_model=Corte, status_code=status.HTTP_201_CREATED) #post
async def crear_corte(caja_id: str, corte: Corte, token: str = Depends(validar_token)):
    caja = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
    if not caja:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    
    corte_dict = corte.model_dump()
    corte_dict["folio"] = generar_folio_corte(db_client.local, corte.sucursal_id)
    
    del corte_dict["id"] #quitar el id para que no se guarde como null
    corte_dict["fondo_inicial"] = Decimal128(str(corte_dict["fondo_inicial"]))
    corte_dict["proximo_fondo"] = Decimal128(str(corte_dict["proximo_fondo"])) if corte_dict["proximo_fondo"] is not None else None
    corte_dict["conteo_pesos"] = Decimal128(str(corte_dict["conteo_pesos"])) if corte_dict["conteo_pesos"] is not None else None
    corte_dict["conteo_dolares"] = Decimal128(str(corte_dict["conteo_dolares"])) if corte_dict["conteo_dolares"] is not None else None
    corte_dict["conteo_debito"] = Decimal128(str(corte_dict["conteo_debito"])) if corte_dict["conteo_debito"] is not None else None
    corte_dict["conteo_credito"] = Decimal128(str(corte_dict["conteo_credito"])) if corte_dict["conteo_credito"] is not None else None
    corte_dict["conteo_transf"] = Decimal128(str(corte_dict["conteo_transf"])) if corte_dict["conteo_transf"] is not None else None
    corte_dict["conteo_total"] = Decimal128(str(corte_dict["conteo_total"])) if corte_dict["conteo_total"] is not None else None
    corte_dict["venta_pesos"] = Decimal128(str(corte_dict["venta_pesos"])) if corte_dict["venta_pesos"] is not None else None
    corte_dict["venta_dolares"] = Decimal128(str(corte_dict["venta_dolares"])) if corte_dict["venta_dolares"] is not None else None
    corte_dict["venta_debito"] = Decimal128(str(corte_dict["venta_debito"])) if corte_dict["venta_debito"] is not None else None
    corte_dict["venta_credito"] = Decimal128(str(corte_dict["venta_credito"])) if corte_dict["venta_credito"] is not None else None
    corte_dict["venta_transf"] = Decimal128(str(corte_dict["venta_transf"])) if corte_dict["venta_transf"] is not None else None
    corte_dict["venta_total"] = Decimal128(str(corte_dict["venta_total"])) if corte_dict["venta_total"] is not None else None
    corte_dict["diferencia"] = Decimal128(str(corte_dict["diferencia"])) if corte_dict["diferencia"] is not None else None  

    # for movimiento in corte_dict["movimiento_caja"]:
    #     movimiento["_id"] = ObjectId()  # Asignar un nuevo ObjectId para cada movimiento
    #     movimiento.pop("id", None)  # Eliminar el campo id si existe, ya que MongoDB genera su propio _id
#
    id = db_client.local.cortes.insert_one(corte_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nuevo_corte = corte_schema(db_client.local.cortes.find_one({"_id":id}))

    # Actualizar la caja agregando el id del nuevo corte a cortes_ids
    db_client.local.cajas.update_one(
        {"_id": ObjectId(caja_id)},
        {"$push": {"cortes_ids": id}}
    )
    
    return Corte(**nuevo_corte)

@router.put("/cortes", status_code=status.HTTP_204_NO_CONTENT)
async def actualizar_corte(corte: Corte, token: str = Depends(validar_token)):
    if not corte.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un corte"
        )
    corte_dict = corte.model_dump()
    del corte_dict["id"]
    
    if corte_dict.get("movimiento_caja"):
        for mov in corte_dict["movimiento_caja"]:
            if mov.get("id"):
                mov["_id"] = ObjectId(mov["id"])
                del mov["id"]
    
    # Convertir Decimals
    campos_decimal = [
        "fondo_inicial", "proximo_fondo", "conteo_pesos", "conteo_dolares",
        "conteo_debito", "conteo_credito", "conteo_transf", "conteo_total",
        "venta_pesos", "venta_dolares", "venta_debito", "venta_credito",
        "venta_transf", "venta_total", "diferencia"
    ]
    
    for campo in campos_decimal:
        valor = getattr(corte, campo)
        if valor is not None:
            corte_dict[campo] = Decimal128(str(valor))
        else:
            corte_dict[campo] = None
    
    try:
        result = db_client.local.cortes.find_one_and_replace(
            {"_id": ObjectId(corte.id)},
            corte_dict
        )
        if not result:
            raise HTTPException(status_code=404, detail='Corte no encontrado')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error al actualizar el corte: {str(e)}'
        )
    return Response(status_code=204)

# ---------------------------------------- MOVIMIENTOS DE CAJA ----------------------------------------
@router.get("/{corte_id}/movimientos")
async def obtener_movimientos(corte_id: str, token: str = Depends(validar_token)):
    # Obtener el corte directamente como diccionario desde MongoDB
    corte_dict = db_client.local.cortes.find_one({"_id": ObjectId(corte_id)})
    if not corte_dict:
        raise HTTPException(status_code=404, detail="Corte no encontrada")
    # Retornar los movimientos usando tu schema para convertir _id a string
    movimientos = corte_dict.get("movimiento_caja", [])
    return movimiento_cajas_schema(movimientos)

@router.post("/{corte_id}/movimientos", status_code=status.HTTP_201_CREATED)
async def agregar_movimiento(corte_id: str, movimiento: dict = Body(...), token: str = Depends(validar_token)):
    movimiento_dict = {
        "_id": ObjectId(),
        "usuario_id": movimiento["usuario_id"],
        "tipo": movimiento["tipo"],
        "monto": float(movimiento["monto"]),
        "motivo": movimiento["motivo"],
        "fecha": movimiento["fecha"]
    }
    # Insertar en el corte
    result = db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$push": {"movimiento_caja": movimiento_dict}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    return movimiento_caja_schema(movimiento_dict)

# ----------------------------------------  OTROS  ----------------------------------------

@router.get("/ventas/{venta_id}/tipo-cambio")
async def obtener_tipo_cambio_por_venta(venta_id: str, token: str = Depends(validar_token)):
    try:
        # Buscar el corte que contiene la venta
        # Primero intentar buscando con la venta_id como string (cuando ventas_ids contiene strings)
        corte = db_client.local.cortes.find_one({"ventas_ids": venta_id})

        # Si no se encuentra, intentar con ObjectId(venta_id) (cuando ventas_ids contiene ObjectId)
        if not corte:
            try:
                venta_obj = ObjectId(venta_id)
                corte = db_client.local.cortes.find_one({"ventas_ids": venta_obj})
            except InvalidId:
                corte = None

        if not corte:
            raise HTTPException(
                status_code=404,
                detail="No se encontró un corte asociado a esta venta"
            )

        # Ahora buscar la caja que contiene el corte
        # Primero intentar con el ObjectId (cuando cortes_ids contiene ObjectId)
        corte_obj_id = corte["_id"]
        caja = db_client.local.cajas.find_one({"cortes_ids": corte_obj_id})

        # Si no se encuentra, intentar con el _id convertido a string (cuando cortes_ids contiene strings)
        if not caja:
            corte_id_str = str(corte_obj_id)
            caja = db_client.local.cajas.find_one({"cortes_ids": corte_id_str})

        if not caja:
            raise HTTPException(
                status_code=404,
                detail="No se encontró una caja asociada al corte"
            )
        
        # Obtener el tipo de cambio
        tipo_cambio = caja.get("tipo_cambio")
        
        if tipo_cambio is None:
            raise HTTPException(
                status_code=404, 
                detail="La caja no tiene tipo de cambio registrado"
            )
        
        return {"tipo_cambio": float(tipo_cambio)}
        
    except InvalidId:
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el tipo de cambio: {str(e)}"
        )


# # prueba!!

# @router.post("/crear-datos-prueba", status_code=status.HTTP_201_CREATED)
# async def crear_datos_prueba(token: str = Depends(validar_token)):
#     """
#     Endpoint de prueba: Crea 200 cajas con fechas incrementales
#     """
#     from datetime import datetime, timedelta
    
#     cajas_creadas = []
#     fecha_base = datetime(2025, 1, 1, 8, 0, 0)  # 1 de enero 2025, 8:00 AM
    
#     try:
#         for i in range(200):
#             # Incrementar 30 minutos por cada caja
#             fecha_apertura = fecha_base + timedelta(minutes=30 * i)
#             fecha_cierre = fecha_apertura + timedelta(hours=8)  # Cierra 8 horas después
            
#             # Variar un poco las ventas para que se vea realista
#             venta_base = 1500.5
#             venta_variada = venta_base + (i * 50.25)  # Incrementa la venta
            
#             caja_dict = {
#                 "folio": generar_folio_caja(db_client.local),
#                 "usuario_id": "682e2177ea82c26a045f21bb",
#                 "sucursal_id": "68d1ceb9b0954102e87eaf9b",
#                 "fecha_apertura": fecha_apertura,
#                 "fecha_cierre": fecha_cierre,
#                 "venta_total": Decimal128(str(venta_variada)),
#                 "estado": "cerrada",
#                 "cortes_ids": [],
#                 "tipo_cambio": 19
#             }
            
#             id_insertado = db_client.local.cajas.insert_one(caja_dict).inserted_id
#             cajas_creadas.append(str(id_insertado))
        
#         return {
#             "mensaje": f"Se crearon {len(cajas_creadas)} cajas de prueba",
#             "total": len(cajas_creadas),
#             "primera_fecha": fecha_base.isoformat(),
#             "ultima_fecha": (fecha_base + timedelta(minutes=30 * 199)).isoformat(),
#             "ids": cajas_creadas[:5]  # Muestra solo los primeros 5 IDs
#         }
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al crear cajas de prueba: {str(e)}"
#         )
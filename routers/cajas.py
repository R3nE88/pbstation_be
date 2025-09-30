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
@router.get("/all", response_model=list[Caja])
async def obtener_cajas(token: str = Depends(validar_token)):
    return cajas_schema(db_client.local.cajas.find())

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
        cortes = db_client.local.cortes.find({"_id": {"$in": cortes_ids}}).sort("fecha_apertura", 1)
        return cortes_schema(cortes)
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

    for movimiento in corte_dict["movimiento_caja"]:
        movimiento["_id"] = ObjectId()  # Asignar un nuevo ObjectId para cada movimiento
        movimiento.pop("id", None)  # Eliminar el campo id si existe, ya que MongoDB genera su propio _id
#
    id = db_client.local.cortes.insert_one(corte_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nuevo_corte = corte_schema(db_client.local.cortes.find_one({"_id":id}))

    # Actualizar la caja agregando el id del nuevo corte a cortes_ids
    db_client.local.cajas.update_one(
        {"_id": ObjectId(caja_id)},
        {"$push": {"cortes_ids": id}}
    )
    
    return Corte(**nuevo_corte)

@router.put("/cortes", response_model=Corte, status_code=status.HTTP_200_OK) #put
async def actualizar_corte(corte: Corte, token: str = Depends(validar_token)):
    if not corte.id:  # Validar si el id está presente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El campo 'id' es obligatorio para actualizar un corte" #se necesita enviar mismo id si no no actualiza
        )
    corte_dict = corte.model_dump()
    del corte_dict["id"]
    corte_dict["fondo_inicial"] = Decimal128(str(corte.fondo_inicial))
    corte_dict["proximo_fondo"] = Decimal128(str(corte.proximo_fondo)) if corte.proximo_fondo is not None else None
    corte_dict["conteo_pesos"] = Decimal128(str(corte.conteo_pesos)) if corte.conteo_pesos is not None else None
    corte_dict["conteo_dolares"] = Decimal128(str(corte.conteo_dolares)) if corte.conteo_dolares is not None else None
    corte_dict["conteo_debito"] = Decimal128(str(corte.conteo_debito)) if corte.conteo_debito is not None else None
    corte_dict["conteo_credito"] = Decimal128(str(corte.conteo_credito)) if corte.conteo_credito is not None else None
    corte_dict["conteo_transf"] = Decimal128(str(corte.conteo_transf)) if corte.conteo_transf is not None else None
    corte_dict["conteo_total"] = Decimal128(str(corte.conteo_total)) if corte.conteo_total is not None else None
    corte_dict["venta_pesos"] = Decimal128(str(corte.venta_pesos)) if corte.venta_pesos is not None else None
    corte_dict["venta_dolares"] = Decimal128(str(corte.venta_dolares)) if corte.venta_dolares is not None else None
    corte_dict["venta_debito"] = Decimal128(str(corte.venta_debito)) if corte.venta_debito is not None else None
    corte_dict["venta_credito"] = Decimal128(str(corte.venta_credito)) if corte.venta_credito is not None else None
    corte_dict["venta_transf"] = Decimal128(str(corte.venta_transf)) if corte.venta_transf is not None else None
    corte_dict["venta_total"] = Decimal128(str(corte.venta_total)) if corte.venta_total is not None else None
    corte_dict["diferencia"] = Decimal128(str(corte.diferencia)) if corte.diferencia is not None else None
    try:
        result = db_client.local.cortes.find_one_and_replace(
            {"_id":ObjectId(corte.id)},
            corte_dict
        )
        if not result:
            raise HTTPException(status_code=404, detail='Corte no encontrado')
    except:        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el corte (put)')
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
    # Preparar movimiento
    movimiento_dict = movimiento.copy()
    movimiento_dict["_id"] = ObjectId()  # generar id
    movimiento_dict["monto"] = float(movimiento_dict["monto"])
    movimiento_dict.pop("id", None)

    # Insertar en el corte
    result = db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$push": {"movimiento_caja": movimiento_dict}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Corte no encontrado")

    return movimiento_caja_schema(movimiento_dict)

@router.put("/{corte_id}/movimientos/{mov_id}")
async def actualizar_movimiento(corte_id: str, mov_id: str, movimiento: dict = Body(...), token: str = Depends(validar_token)):
    movimiento["_id"] = ObjectId(mov_id)
    movimiento["monto"] = float(movimiento["monto"])

    result = db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id), "movimiento_caja._id": ObjectId(mov_id)},
        {"$set": {"movimiento_caja.$": movimiento}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento o corte no encontrado")

    return {
        "mensaje": "Movimiento actualizado",
        "movimiento": movimiento_caja_schema(movimiento)
    }

@router.delete("/{corte_id}/movimientos/{mov_id}")
async def eliminar_movimiento(corte_id: str, mov_id: str, token: str = Depends(validar_token)):
    result = db_client.local.cortes.update_one(
        {"_id": ObjectId(corte_id)},
        {"$pull": {"movimiento_caja": {"_id": ObjectId(mov_id)}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento o corte no encontrado")
    return {"mensaje": "Movimiento eliminado", "movimiento_id": mov_id}

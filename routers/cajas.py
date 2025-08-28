from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Body
from core.database import db_client
from generador_folio import generar_folio_caja, obtener_nombre_sucursal
from models.caja import Caja
from schemas.caja import cajas_schema, caja_schema
from schemas.movimiento_caja import movimiento_caja_schema, movimiento_cajas_schema
from bson.decimal128 import Decimal128
from validar_token import validar_token 

router = APIRouter(prefix="/cajas", tags=["cajas"])

@router.get("/all", response_model=list[Caja])
async def obtener_cajas(token: str = Depends(validar_token)):
    return cajas_schema(db_client.local.cajas.find())


@router.get("/{id}") #path
async def obtener_caja_path(id: str, token: str = Depends(validar_token)):
    return search_caja("_id", ObjectId(id))
    

@router.get("/") #Query
async def obtener_caja_query(id: str, token: str = Depends(validar_token)):
    return search_caja("_id", ObjectId(id))


@router.post("/", response_model=Caja, status_code=status.HTTP_201_CREATED) #post
async def crear_caja(caja: Caja, token: str = Depends(validar_token)):
    caja_dict = caja.model_dump()

    #generacion de folio
    caja_dict["folio"] = generar_folio_caja(db_client.local)

    del caja_dict["id"] #quitar el id para que no se guarde como null
    caja_dict["efectivo_apertura"] = Decimal128(str(caja_dict["efectivo_apertura"]))
    caja_dict["efectivo_cierre"] = Decimal128(str(caja_dict["efectivo_cierre"])) if caja_dict["efectivo_cierre"] is not None else None
    caja_dict["total_teorico"] = Decimal128(str(caja_dict["total_teorico"])) if caja_dict["total_teorico"] is not None else None
    caja_dict["diferencia"] = Decimal128(str(caja_dict["diferencia"])) if caja_dict["diferencia"] is not None else None

    for movimiento in caja_dict["movimiento_caja"]:
        movimiento["_id"] = ObjectId()  # Asignar un nuevo ObjectId para cada movimiento
        #movimiento["monto"] = Decimal128(str(movimiento["monto"]))
        movimiento.pop("id", None)  # Eliminar el campo id si existe, ya que MongoDB genera su propio _id

    id = db_client.local.cajas.insert_one(caja_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    nueva_caja = caja_schema(db_client.local.cajas.find_one({"_id":id}))
    
    return Caja(**nueva_caja)


#@router.put("/", response_model=Caja, status_code=status.HTTP_200_OK) #put
#async def actualizar_caja(caja: Caja, token: str = Depends(validar_token)):
#    if not caja.id:  # Validar si el id está presente
#        raise HTTPException(
#            status_code=status.HTTP_400_BAD_REQUEST, 
#            detail="El campo 'id' es obligatorio para actualizar una caja" #se necesita enviar mismo id si no no actualiza
#        )
#
#    caja_dict = caja.model_dump()
#    del caja_dict["id"]
#    caja_dict["efectivo_apertura"] = Decimal128(str(caja.efectivo_apertura)) #caja_dict["efectivo_apertura"] = Decimal128(caja_dict["efectivo_apertura"])
#    caja_dict["efectivo_cierre"] = Decimal128(str(caja.efectivo_cierre)) if caja.efectivo_cierre is not None else None
#    caja_dict["total_teorico"] = Decimal128(str(caja.total_teorico)) if caja.total_teorico is not None else None
#    caja_dict["diferencia"] = Decimal128(str(caja.diferencia)) if caja.diferencia is not None else None
#    for movimiento in caja_dict["movimiento_caja"]:
#        if "_id" not in movimiento: #ESTO NO FUNCIONA PORQUE SIEMPRE CAMBIE EL ID DE MOVIMIENTO
#            movimiento["_id"] = ObjectId()
#        movimiento["monto"] = Decimal128(str(movimiento["monto"]))
#        
#    try:
#        db_client.local.cajas.find_one_and_replace({"_id":ObjectId(caja.id)}, caja_dict)
#    except:        
#        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro al caja (put)')
#    
#    #await manager.broadcast(f"put-caja:{str(ObjectId(caja.id))}") #Notificar a todos
#    return search_caja("_id", ObjectId(caja.id))


def search_caja(field: str, key):
    try:
        caja = db_client.local.cajas.find_one({field: key})
        if not caja:  # Verificar si no se encontró la caja
            return None
        return Caja(**caja_schema(caja))  # el ** sirve para pasar los valores del diccionario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error al buscar la caja: {str(e)}')
    
    # ---------------------------------------- MOVIMIENTOS DE CAJA ----------------------------------------

@router.get("/{caja_id}/movimientos")
async def obtener_movimientos(caja_id: str, token: str = Depends(validar_token)):
    # Obtener la caja directamente como diccionario desde MongoDB
    caja_dict = db_client.local.cajas.find_one({"_id": ObjectId(caja_id)})
    if not caja_dict:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    
    # Retornar los movimientos usando tu schema para convertir _id a string
    movimientos = caja_dict.get("movimiento_caja", [])
    return movimiento_cajas_schema(movimientos)


@router.post("/{caja_id}/movimientos", status_code=status.HTTP_201_CREATED)
async def agregar_movimiento(caja_id: str, movimiento: dict = Body(...), token: str = Depends(validar_token)):
    # Preparar movimiento
    movimiento_dict = movimiento.copy()
    movimiento_dict["_id"] = ObjectId()  # generar id
    movimiento_dict["monto"] = float(movimiento_dict["monto"])  # asegurar float
    movimiento_dict.pop("id", None)  # eliminar id si viene

    # Insertar en la caja
    result = db_client.local.cajas.update_one(
        {"_id": ObjectId(caja_id)},
        {"$push": {"movimiento_caja": movimiento_dict}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Caja no encontrada")

    return movimiento_caja_schema(movimiento_dict)

@router.put("/{caja_id}/movimientos/{mov_id}")
async def actualizar_movimiento(caja_id: str, mov_id: str, movimiento: dict = Body(...), token: str = Depends(validar_token)):
    movimiento["_id"] = ObjectId(mov_id)  # mantener el mismo id
    movimiento["monto"] = float(movimiento["monto"])
    
    result = db_client.local.cajas.update_one(
        {"_id": ObjectId(caja_id), "movimiento_caja._id": ObjectId(mov_id)},
        {"$set": {"movimiento_caja.$": movimiento}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento o caja no encontrada")

    return {
        "mensaje": "Movimiento actualizado",
        "movimiento": movimiento_caja_schema(movimiento)
    }

@router.delete("/{caja_id}/movimientos/{mov_id}")
async def eliminar_movimiento(caja_id: str, mov_id: str, token: str = Depends(validar_token)):
    result = db_client.local.cajas.update_one(
        {"_id": ObjectId(caja_id)},
        {"$pull": {"movimiento_caja": {"_id": ObjectId(mov_id)}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento o caja no encontrada")

    return {"mensaje": "Movimiento eliminado", "movimiento_id": mov_id}

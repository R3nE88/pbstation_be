import re
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException

#para obtener el folio de la venta
def abreviar_sucursal(nombre: str) -> str:
    # Elimina la palabra "sucursal" en cualquier capitalización
    nombre_limpio = re.sub(r'\bsucursal\b', '', nombre, flags=re.IGNORECASE).strip()
    # Busca la primera letra
    letra = re.search(r'[A-Za-z]', nombre_limpio)
    if letra:
        return letra.group(0).upper()
    # Si no hay letras, busca el número
    numero = re.search(r'\d+', nombre_limpio)
    if numero:
        return f"S{numero.group(0)}"
    # Fallback
    return "S0"

def obtener_consecutivo(db, sucursal_abreviada: str, fecha: str) -> int:
    pattern = f"^{sucursal_abreviada}{fecha}"
    folios_hoy = db.ventas.count_documents({"folio": {"$regex": pattern}})
    return folios_hoy + 1

def obtener_consecutivo_cotizacion(db, sucursal_abreviada: str, fecha: str) -> int:
    pattern = f"^COT{sucursal_abreviada}{fecha}"
    print(f"Usando patrón regex: {pattern}")
    folios_hoy = db.cotizaciones.count_documents({"folio": {"$regex": pattern}})
    print(f"Coincidencias encontradas: {folios_hoy}")
    return folios_hoy + 1

def generar_folio(db, nombre_sucursal: str) -> str:
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    fecha = datetime.now().strftime("%y%m%d")
    consecutivo = obtener_consecutivo(db, sucursal_abreviada, fecha)
    return f"{sucursal_abreviada}{fecha}{consecutivo:03d}"

def generar_folio_cotizacion(db, nombre_sucursal: str) -> str:
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    fecha = datetime.now().strftime("%y%m%d")
    consecutivo = obtener_consecutivo_cotizacion(db, sucursal_abreviada, fecha)
    return f"COT{sucursal_abreviada}{fecha}{consecutivo:03d}"

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


# #para obtener el folio de la cotizacion
# def abreviar_sucursal(nombre: str) -> str:
#     match = re.search(r'(\d+\w*)', nombre)
#     if match:
#         return f"S{match.group(1)}"
#     return "S0"

# def obtener_consecutivo(db, sucursal_abreviada: str, fecha: str) -> int:
#     pattern = f"^{sucursal_abreviada}-{fecha}-"
#     folios_hoy = db.cotizaciones.count_documents({"folio": {"$regex": pattern}})
#     return folios_hoy + 1

# def generar_folio(db, nombre_sucursal: str) -> str:
#     sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
#     fecha = datetime.now().strftime("%y%m%d")
#     consecutivo = obtener_consecutivo(db, sucursal_abreviada, fecha)
#     return f"COT{sucursal_abreviada}-{fecha}-{consecutivo:05d}"

# def obtener_nombre_sucursal(db, sucursal_id_str: str) -> str:
#     try:
#         sucursal_id = ObjectId(sucursal_id_str)
#     except:
#         raise HTTPException(status_code=400, detail="ID de sucursal inválido")

#     sucursal = db.sucursales.find_one({"_id": sucursal_id})
#     if not sucursal:
#         raise HTTPException(status_code=404, detail="Sucursal no encontrada")
#     return sucursal["nombre"]
# # aqui termina la funcion para generar el folio
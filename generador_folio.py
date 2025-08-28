import re
import string
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException

BASE36 = string.digits + string.ascii_uppercase  # 0-9 + A-Z

def a_base36(num: int, length: int) -> str:
    """Convierte un número a base36 con padding fijo."""
    if num < 0:
        raise ValueError("Número no puede ser negativo")
    res = ""
    while num > 0:
        num, rem = divmod(num, 36)
        res = BASE36[rem] + res
    return res.rjust(length, "0")

def abreviar_sucursal(nombre: str) -> str:
    """Devuelve la primera letra válida del nombre de la sucursal."""
    nombre_limpio = re.sub(r'\bsucursal\b', '', nombre, flags=re.IGNORECASE).strip()
    letra = re.search(r'[A-Za-z]', nombre_limpio)
    if letra:
        return letra.group(0).upper()
    numero = re.search(r'\d+', nombre_limpio)
    if numero:
        return f"S{numero.group(0)}"
    return "S0"

def obtener_fecha_cod(hoy: datetime) -> str:
    """Devuelve el código de fecha (día del año en base36, 2 dígitos)."""
    dia_anual = hoy.timetuple().tm_yday  # 1–366
    return a_base36(dia_anual, 2)

def obtener_siguiente_consecutivo(db, coleccion: str, prefijo: str, hoy: datetime) -> int:
    """Busca el último folio del día en la colección indicada y devuelve el siguiente consecutivo."""
    fecha_cod = obtener_fecha_cod(hoy)
    pattern = f"^{prefijo}{fecha_cod}"
    ultimo = db[coleccion].find_one({"folio": {"$regex": pattern}}, sort=[("folio", -1)])
    if not ultimo:
        return 0
    try:
        consec_str = ultimo["folio"][-2:]  # últimos 2 caracteres en base36
        return int(consec_str, 36) + 1
    except Exception:
        return 0

def generar_folio_venta(db, nombre_sucursal: str) -> str:
    """Genera un folio de 5 caracteres para ventas."""
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    hoy = datetime.now()
    consecutivo = obtener_siguiente_consecutivo(db, "ventas", sucursal_abreviada[0], hoy)

    fecha_cod = obtener_fecha_cod(hoy)
    consecutivo_cod = a_base36(consecutivo, 2)

    return f"{sucursal_abreviada[0]}{fecha_cod}{consecutivo_cod}"

def generar_folio_cotizacion(db) -> str:
    """Genera un folio de 5 caracteres para cotizaciones (siempre inicia con 'CZ')."""
    hoy = datetime.now()
    consecutivo = obtener_siguiente_consecutivo(db, "cotizaciones", "CZ", hoy)

    fecha_cod = obtener_fecha_cod(hoy)
    consecutivo_cod = a_base36(consecutivo, 2)

    return f"CZ{fecha_cod}{consecutivo_cod}"

def generar_folio_caja(db) -> str:
    """Genera un folio de 5 caracteres para cajas (siempre inicia con 'CJ')."""
    hoy = datetime.now()
    consecutivo = obtener_siguiente_consecutivo(db, "cajas", "CJ", hoy)

    fecha_cod = obtener_fecha_cod(hoy)
    consecutivo_cod = a_base36(consecutivo, 2)

    return f"CJ{fecha_cod}{consecutivo_cod}"

def obtener_nombre_sucursal(db, sucursal_id_str: str) -> str:
    """Devuelve el nombre de la sucursal desde Mongo."""
    try:
        sucursal_id = ObjectId(sucursal_id_str)
    except:
        raise HTTPException(status_code=400, detail="ID de sucursal inválido")

    sucursal = db.sucursales.find_one({"_id": sucursal_id})
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return sucursal["nombre"]

import string
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

# ------------------------------------------------------------------
# Helpers de formato y abreviación
# ------------------------------------------------------------------

def obtener_siguiente_prefijo(db) -> str:
    seq = _get_next_seq_atomic(db, "sucursales:prefijo")
    index = seq - 1
    return index_to_base26_letters(index)

def _normalize_prefijo(prefijo: str) -> str:
    if not prefijo:
        return "0"
    return str(prefijo).strip().upper().rstrip('-')

def obtener_prefijo_por_id(db, sucursal_id) -> str:
    try:
        oid = ObjectId(str(sucursal_id))
    except Exception:
        doc = db.sucursales.find_one({"_id": sucursal_id}, {"prefijo_folio": 1})
    else:
        doc = db.sucursales.find_one({"_id": oid}, {"prefijo_folio": 1})
    if not doc:
        return "0"
    return _normalize_prefijo(doc.get("prefijo_folio"))

def fecha_YYMMDD(hoy: datetime) -> str:
    return hoy.strftime("%y%m%d")

def anio_YYY(hoy: datetime) -> str:
    return hoy.strftime("%j")

def anio_YY(hoy: datetime) -> str:
    return hoy.strftime("%y")

def pad_number(num: int, width: int) -> str:
    return str(num).zfill(width)

# ------------------------------------------------------------------
# Conversión de índices a letras
# ------------------------------------------------------------------

ALPHABET = string.ascii_uppercase  # 'A'..'Z' (len=26)

def index_to_base26_letters(index: int) -> str:
    if index < 0:
        raise ValueError("index debe ser >= 0")
    letters = []
    # Usamos forma donde 0 -> 'A'
    while True:
        letters.append(ALPHABET[index % 26])
        index = index // 26 - 1
        if index < 0:
            break
    return ''.join(reversed(letters))

# ------------------------------------------------------------------
# Contador atómico en MongoDB
# ------------------------------------------------------------------

def _get_next_seq_atomic(db, key: str) -> int:
    result = db.counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return int(result["seq"])

def obtener_siguiente_consecutivo(db, coleccion: str, prefijo: str, hoy: datetime) -> int:
    coleccion = coleccion.lower()
    if coleccion == "ventas":
        # prefijo se espera ser la letra de sucursal
        suc = (prefijo or "S")[0]
        key = f"ventas:{suc}:{fecha_YYMMDD(hoy)}"  # YYYYMMDD para legibilidad
    elif coleccion == "cotizaciones":
        key = f"cotizaciones:{fecha_YYMMDD(hoy)}"
    elif coleccion == "cajas" or coleccion == "caja":
        key = f"cajas:{anio_YY(hoy)}"
    elif coleccion == "cortes" or coleccion == "corte":
        suc = (prefijo or "S")[0]
        key = f"cortes:{suc}:{anio_YY(hoy)}{anio_YYY(hoy)}"
    else:
        key = f"{coleccion}:{prefijo}:{fecha_YYMMDD(hoy)}"
    return _get_next_seq_atomic(db, key)

# ------------------------------------------------------------------
# Formateadores concretos por tipo de folio
# ------------------------------------------------------------------

def generar_folio_venta(db, sucursal_id) -> str:
    prefijo = obtener_prefijo_por_id(db, sucursal_id)   # 'A', 'AA', o 'S' fallback
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "ventas", prefijo, hoy)  # tu función atómica existente
    consecutivo = pad_number(seq, 2)
    return f"{fecha_YYMMDD(hoy)}{prefijo}{consecutivo}"

def generar_folio_cotizacion(db) -> str:
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cotizaciones", "CT", hoy)
    consecutivo = pad_number(seq, 3)
    return f"{fecha_YYMMDD(hoy)}{consecutivo}"

def generar_folio_caja(db) -> str:
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cajas", "CJ", hoy)
    return f"CJ{anio_YY(hoy)}{pad_number(seq, 3)}"

def generar_folio_corte(db, sucursal_id: str) -> str:
    prefijo = obtener_prefijo_por_id(db, sucursal_id)
    suc_char = prefijo
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cortes", suc_char, hoy)
    return f"{anio_YY(hoy)}{anio_YYY(hoy)}{suc_char}{pad_number(seq, 1)}"

# ------------------------------------------------------------------
# Ejemplos de uso (comentados)
# ------------------------------------------------------------------
# from pymongo import MongoClient
# from core.database import db_client
# print('Ejemplo de venta')
# sucursal_id = '68d1cedcb0954102e87eaf9c'
# for _ in range(1):
#     print(generar_folio_venta(db_client.local, sucursal_id))
#     print(generar_folio_cotizacion(db_client.local))
#     print(generar_folio_caja(db_client.local))
#     print(generar_folio_corte(db_client.local, sucursal_id))#
# #
# 7: 68d1ceb9b0954102e87eaf9b
# 38: 68d1cedcb0954102e87eaf9c
# 5: 68d1cf02b0954102e87eaf9d

#Formatos de folios
#Venta: [fecha][Sucursal][consecutivo_2]
#ejemplo A250922029

#Cotizaciones: [CT][fecha][consecutivo_3]
#ejemplo 250922023

#Caja: [CJ][Año][consecutivo_3]
#ejemplo CJ25019

#Corte: [Año][DiaDelAño][Sucusal][consecutivo_1]
#ejemplo TA25081401
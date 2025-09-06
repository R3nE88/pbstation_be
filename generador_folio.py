import re
import string
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

# ------------------------------------------------------------------
# Helpers de formato y abreviación
# ------------------------------------------------------------------

def abreviar_sucursal(nombre: str) -> str:
    """Devuelve la primera letra válida del nombre de la sucursal (mayúscula).
    Si no hay letra devuelve 'S' seguido del número si existe o 'S0'."""
    nombre_limpio = re.sub(r'\bsucursal\b', '', nombre, flags=re.IGNORECASE).strip()
    letra = re.search(r'[A-Za-z]', nombre_limpio)
    if letra:
        return letra.group(0).upper()
    numero = re.search(r'\d+', nombre_limpio)
    if numero:
        return f"S{numero.group(0)}"
    return "S0"

def fecha_YYMMDD(hoy: datetime) -> str:
    """Devuelve fecha en formato YYMMDD (ej: 250209)."""
    return hoy.strftime("%y%m%d")

def anio_YY(hoy: datetime) -> str:
    """Devuelve año en formato YY (ej: 25)."""
    return hoy.strftime("%y")

def pad_number(num: int, width: int) -> str:
    """Devuelve número con padding de ceros a la izquierda."""
    return str(num).zfill(width)

# ------------------------------------------------------------------
# Conversión de índices a letras
# ------------------------------------------------------------------

ALPHABET = string.ascii_uppercase  # 'A'..'Z' (len=26)

def index_to_base26_letters(index: int) -> str:
    """Convierte un índice 0-based a letras base-26 variable length.
    0 -> 'A', 25 -> 'Z', 26 -> 'AA', etc."""
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

def index_to_fixed_letters(index: int, width: int) -> str:
    """Convierte un índice 0-based a un bloque de letras con ancho fijo.
    0 -> 'A' repeated (por ejemplo width=2 -> 'AA'), 1 -> 'AB', ... hasta 'ZZ'."""
    max_values = 26 ** width
    if index < 0 or index >= max_values:
        raise ValueError(f"index fuera de rango (0..{max_values-1}) para width={width}")
    # Convertir index a base-26 con ancho fijo
    letters = []
    for pos in range(width):
        div = 26 ** (width - pos - 1)
        digit = index // div
        letters.append(ALPHABET[digit])
        index -= digit * div
    return ''.join(letters)

# ------------------------------------------------------------------
# Contador atómico en MongoDB
# ------------------------------------------------------------------

def _get_next_seq_atomic(db, key: str) -> int:
    """Usa la colección 'counters' para incrementar atómicamente y devolver el seq (empieza en 1)."""
    # Ejemplo de documento en counters: { _id: "ventas:M:20250209", seq: 12 }
    result = db.counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    # Si se creó nuevo documento, result['seq'] será 1 (porque $inc lo creó en 1)
    return int(result["seq"])

# ------------------------------------------------------------------
# Función de compatibilidad: obtener_siguiente_consecutivo
# (mantiene nombre usado por tu código previo; ahora es atómica)
# ------------------------------------------------------------------

def obtener_siguiente_consecutivo(db, coleccion: str, prefijo: str, hoy: datetime) -> int:
    """
    Calcula la clave para counters según la colección y devuelve el siguiente seq atómico.
    - ventas: reinicio por día y por sucursal -> key: "ventas:{sucursal}:{YYYYMMDD}"
    - cotizaciones: reinicio por día (global) -> key: "cotizaciones:{YYYYMMDD}"
    - cajas: reinicio por año -> key: "cajas:{YY}"
    - cortes: reinicio por año y por sucursal -> key: "cortes:{sucursal}:{YY}"
    Nota: 'prefijo' se interpreta como sucursal (o como prefijo cuando corresponda).
    """
    coleccion = coleccion.lower()
    if coleccion == "ventas":
        # prefijo se espera ser la letra de sucursal
        suc = (prefijo or "S")[0]
        key = f"ventas:{suc}:{hoy.strftime('%Y%m%d')}"  # YYYYMMDD para legibilidad
    elif coleccion == "cotizaciones":
        key = f"cotizaciones:{hoy.strftime('%Y%m%d')}"
    elif coleccion == "cajas" or coleccion == "caja":
        key = f"cajas:{anio_YY(hoy)}"
    elif coleccion == "cortes" or coleccion == "corte":
        suc = (prefijo or "S")[0]
        key = f"cortes:{suc}:{anio_YY(hoy)}"
    else:
        # fallback general: usar coleccion + prefijo + fecha
        key = f"{coleccion}:{prefijo}:{hoy.strftime('%Y%m%d')}"
    return _get_next_seq_atomic(db, key)

# ------------------------------------------------------------------
# Formateadores concretos por tipo de folio
# ------------------------------------------------------------------

def generar_folio_venta(db, nombre_sucursal: str) -> str:
    """
    Formato: [Sucursal][YYMMDD][Consecutivo 3 dígitos]
    Ej: M250209001
    Consecutivo inicia en 1 y reinicia cada día por sucursal.
    """
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    suc_char = sucursal_abreviada[0]  # asumimos 1 caracter para folio
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "ventas", suc_char, hoy)  # atómico
    consecutivo = pad_number(seq, 3)  # 001
    return f"{suc_char}{fecha_YYMMDD(hoy)}{consecutivo}"

def generar_folio_cotizacion(db) -> str:
    """
    Formato: CT[YYMMDD][Letra(s)][Número]
    Ej: CT250209A1
    Consecutivo inicia en 1 y reinicia cada día (global).
    Conversión: seq -> letra_block + number_in_block, con 9 números por letra (1..9).
      seq 1..9 -> A1..A9
      seq 10 -> B1
      etc.
    Si se exceden 26 letras se generan letras múltiples (AA, AB, ...).
    """
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cotizaciones", "CT", hoy)
    # número por letra: 1..9
    numbers_per_letter = 9
    letter_index = (seq - 1) // numbers_per_letter  # 0-based
    number_in_block = ((seq - 1) % numbers_per_letter) + 1  # 1..9
    letter_block = index_to_base26_letters(letter_index)  # puede ser 'A', 'B' ... 'Z', 'AA', ...
    return f"CT{fecha_YYMMDD(hoy)}{letter_block}{number_in_block}"

def generar_folio_caja(db) -> str:
    """
    Formato: CJ[YY][Consecutivo 3 dígitos]
    Ej: CJ25001  (CJ + 25 + 001)
    Consecutivo inicia en 1 y reinicia por año.
    """
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cajas", "CJ", hoy)
    return f"CJ{anio_YY(hoy)}{pad_number(seq, 3)}"

def generar_folio_corte(db, nombre_sucursal: str) -> str:
    """
    Formato: X[Sucursal][YY][2letras][número]
    Ej: XM25AA1
    Consecutivo inicia en 1 y reinicia por año y por sucursal.
    Conversión:
      seq -> block_index (0-based) y number_in_block (1..9)
      block_index -> 2 letras fijas (AA, AB, ... ZZ)
    """
    sucursal_abreviada = abreviar_sucursal(nombre_sucursal)
    suc_char = sucursal_abreviada[0]
    hoy = datetime.now()
    seq = obtener_siguiente_consecutivo(db, "cortes", suc_char, hoy)
    numbers_per_block = 9
    block_index = (seq - 1) // numbers_per_block  # 0-based block index which maps to 2-letter code
    number_in_block = ((seq - 1) % numbers_per_block) + 1  # 1..9

    # Convertir block_index a 2 letras fijas (AA .. ZZ)
    # Nota: esto limita a 26*26 bloques; si necesitas más, podemos extender.
    two_letters = index_to_fixed_letters(block_index, 2)
    return f"X{suc_char}{anio_YY(hoy)}{two_letters}{number_in_block}"

# ------------------------------------------------------------------
# Util: obtener nombre de sucursal desde Mongo (tu función original)
# ------------------------------------------------------------------

def obtener_nombre_sucursal(db, sucursal_id_str: str) -> str:
    """Devuelve el nombre de la sucursal desde Mongo."""
    try:
        sucursal_id = ObjectId(sucursal_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de sucursal inválido")

    sucursal = db.sucursales.find_one({"_id": sucursal_id})
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return sucursal["nombre"]

# ------------------------------------------------------------------
# Ejemplos de uso (comentados)
# ------------------------------------------------------------------
# from pymongo import MongoClient
# client = MongoClient("mongodb://localhost:27017")
# db = client.printerboy
#
# print(generar_folio_venta(db, "Sucursal Matriz"))
# print(generar_folio_cotizacion(db))
# print(generar_folio_caja(db))
# print(generar_folio_corte(db, "Sucursal Matriz"))
#
# Asegúrate de que la colección 'counters' tenga permisos de escritura.



#Formatos de folios
#Venta: [Sucursal][fecha][consecutivo]
#ejemplo M250209001

#Cotizaciones: [CT][fecha][consecutivo con letra]
#ejemplo CT250209A1

#Caja: [CJ][Año][consecutivo]
#ejemplo CJ25001

#Corte: [X][Sucusal][Año][consecutivo con 2 letras (mas margen)]
#ejemplo XM25AA1
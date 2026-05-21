import os
import re
import uuid
from typing import Iterable

from fastapi import HTTPException, UploadFile


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_SIZE_MB = 500
MAX_TOTAL_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
EXTENSIONES_PERMITIDAS = {
    "pdf", "jpg", "jpeg", "png", "webp", "svg", "ai", "eps", "psd",
    "tif", "tiff", "zip", "rar", "7z"
}


def _upload_base_abs() -> str:
    return os.path.abspath(UPLOAD_DIR)


def _sanear_nombre_archivo(filename: str) -> str:
    nombre = os.path.basename(filename or "").strip()
    nombre = re.sub(r"[^A-Za-z0-9._ -]", "_", nombre).replace("..", "_")
    if not nombre or nombre in {".", ".."}:
        raise HTTPException(status_code=400, detail="Nombre de archivo invalido")
    ext = os.path.splitext(nombre)[1].lstrip(".").lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(status_code=400, detail=f"Extension no permitida: {ext}")
    return nombre


def ruta_archivo_absoluta(ruta_relativa: str) -> str:
    ruta_limpia = (ruta_relativa or "").replace("\\", "/").lstrip("/")
    if not ruta_limpia or ".." in ruta_limpia.split("/"):
        raise HTTPException(status_code=400, detail="Ruta de archivo invalida")
    base = _upload_base_abs()
    ruta = os.path.abspath(os.path.join(base, *ruta_limpia.split("/")))
    if os.path.commonpath([base, ruta]) != base:
        raise HTTPException(status_code=400, detail="Ruta de archivo invalida")
    return ruta


def _ruta_relativa(pedido_id: str, nombre: str) -> str:
    return f"{pedido_id}/{nombre}"


def _nombre_unico_archivo(nombre_original: str) -> str:
    stem, ext = os.path.splitext(nombre_original)
    return f"{stem}_{uuid.uuid4().hex[:12]}{ext}"


def eliminar_rutas(rutas: Iterable[str]) -> None:
    for ruta in rutas:
        try:
            ruta_abs = ruta_archivo_absoluta(ruta)
            if os.path.exists(ruta_abs):
                os.remove(ruta_abs)
        except (HTTPException, OSError) as e:
            print(f"Advertencia: No se pudo eliminar archivo huerfano {ruta}: {str(e)}")


async def guardar_uploads(pedido_id: str, archivos: list[UploadFile]) -> list[dict]:
    pedido_dir_relativo = pedido_id
    pedido_dir = ruta_archivo_absoluta(pedido_dir_relativo)
    os.makedirs(pedido_dir, exist_ok=True)
    archivos_guardados = []
    rutas_guardadas = []
    total_size = 0

    try:
        for archivo in archivos:
            nombre_original = _sanear_nombre_archivo(archivo.filename)
            nombre = _nombre_unico_archivo(nombre_original)
            ruta_relativa = _ruta_relativa(pedido_id, nombre)
            ruta = ruta_archivo_absoluta(ruta_relativa)
            ruta_temp_relativa = _ruta_relativa(pedido_id, f".{nombre}.tmp")
            ruta_temp = ruta_archivo_absoluta(ruta_temp_relativa)
            size = 0

            try:
                with open(ruta_temp, "xb") as buffer:
                    while True:
                        chunk = await archivo.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        size += len(chunk)
                        total_size += len(chunk)
                        if total_size > MAX_TOTAL_SIZE:
                            raise HTTPException(
                                status_code=413,
                                detail=f"El tamano total excede el limite de {MAX_UPLOAD_SIZE_MB}MB"
                            )
                        buffer.write(chunk)
                os.replace(ruta_temp, ruta)
            finally:
                if os.path.exists(ruta_temp):
                    os.remove(ruta_temp)

            rutas_guardadas.append(ruta_relativa)
            archivos_guardados.append({
                "nombre": nombre,
                "nombre_original": nombre_original,
                "ruta": ruta_relativa,
                "tipo": os.path.splitext(nombre_original)[1].lstrip(".").lower(),
                "tamano": size
            })
    except Exception:
        eliminar_rutas(rutas_guardadas)
        raise

    return archivos_guardados


def limpiar_archivos_huerfanos(db) -> dict:
    rutas_referenciadas = set()
    for pedido in db.pedidos.find({}, {"archivos.ruta": 1}):
        for archivo in pedido.get("archivos", []):
            ruta = archivo.get("ruta")
            if not ruta:
                continue
            try:
                rutas_referenciadas.add(ruta_archivo_absoluta(ruta))
            except HTTPException:
                continue

    archivos_eliminados = 0
    carpetas_eliminadas = 0
    base = _upload_base_abs()
    if not os.path.exists(base):
        return {
            "archivos_eliminados": archivos_eliminados,
            "carpetas_eliminadas": carpetas_eliminadas,
        }

    for root, _, files in os.walk(base):
        for filename in files:
            ruta = os.path.abspath(os.path.join(root, filename))
            if ruta in rutas_referenciadas:
                continue
            try:
                os.remove(ruta)
                archivos_eliminados += 1
            except OSError as e:
                print(f"Advertencia: No se pudo eliminar archivo huerfano {ruta}: {str(e)}")

    for root, dirs, _ in os.walk(base, topdown=False):
        for dirname in dirs:
            ruta_dir = os.path.join(root, dirname)
            try:
                os.rmdir(ruta_dir)
                carpetas_eliminadas += 1
            except OSError:
                pass

    return {
        "archivos_eliminados": archivos_eliminados,
        "carpetas_eliminadas": carpetas_eliminadas,
    }

from io import BytesIO
import zipfile
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Header
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import os
import json
from core.database import db_client
from models.pedido import Pedido
from schemas.pedido import pedido_schema, pedidos_schema
from validar_token import validar_token
from routers.websocket import manager
from fastapi.responses import StreamingResponse
from generador_folio import generar_folio_pedido

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_SIZE_GB = 5
MAX_TOTAL_SIZE = MAX_UPLOAD_SIZE_GB * 1024 * 1024 * 1024


@router.get("/all", response_model=List[Pedido])
async def obtener_pedidos(token: str = Depends(validar_token)):
    pedidos = db_client.local.pedidos.find().sort("fecha", -1)
    return pedidos_schema(pedidos)


@router.post("/", response_model=Pedido, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    pedido: str = Form(...),
    archivos: Optional[List[UploadFile]] = File(None),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    try:
        pedido_data = json.loads(pedido)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Datos del pedido inválidos")
    
    estado = pedido_data.get('estado', 'pendiente')
    if not archivos and estado != 'en espera':
        raise HTTPException(
            status_code=400,
            detail="Los pedidos deben tener archivos o estar en estado 'en espera'"
        )
    
    archivos_temp = []
    if archivos:
        total_size = 0
        for archivo in archivos:
            content = await archivo.read()
            total_size += len(content)
            archivos_temp.append({
                'content': content,
                'filename': archivo.filename,
                'size': len(content)
            })
        
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"El tamaño total excede el límite de {MAX_UPLOAD_SIZE_GB}GB"
            )
    
    folio = generar_folio_pedido(db_client.local, pedido_data['sucursal_id'])

    pedido_temp = {
        "cliente_id": pedido_data['cliente_id'],
        "usuario_id": pedido_data['usuario_id'],
        "sucursal_id": pedido_data['sucursal_id'],
        "venta_id": pedido_data.get('venta_id', ''),
        "folio": folio,
        "descripcion": pedido_data.get('descripcion', ''),
        "fecha": datetime.fromisoformat(pedido_data['fecha']),
        "fecha_entrega": datetime.fromisoformat(pedido_data['fecha_entrega']),
        "archivos": [],
        "estado": estado
    }

    result = db_client.local.pedidos.insert_one(pedido_temp)
    pedido_id = str(result.inserted_id)

    if archivos_temp:
        pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
        os.makedirs(pedido_dir, exist_ok=True)
        archivos_guardados = []

        for archivo_temp in archivos_temp:
            nombre = archivo_temp['filename']
            ext = os.path.splitext(nombre)[1]
            ruta = os.path.join(pedido_dir, nombre)
            
            try:
                with open(ruta, "wb") as buffer:
                    buffer.write(archivo_temp['content'])
                
                archivos_guardados.append({
                    "nombre": nombre,
                    "ruta": ruta,
                    "tipo": ext.lstrip("."),
                    "tamano": archivo_temp['size']
                })
            except Exception as e:
                import shutil
                if os.path.exists(pedido_dir):
                    shutil.rmtree(pedido_dir)
                db_client.local.pedidos.delete_one({"_id": ObjectId(pedido_id)})
                raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")

        db_client.local.pedidos.update_one(
            {"_id": ObjectId(pedido_id)},
            {"$set": {"archivos": archivos_guardados}}
        )

    nuevo_pedido = pedido_schema(db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)}))
    await manager.broadcast(f"post-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    return Pedido(**nuevo_pedido)


@router.patch("/{pedido_id}/archivos", response_model=Pedido)
async def agregar_archivos_pedido(
    pedido_id: str,
    archivos: List[UploadFile] = File(...),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    total_size = 0
    archivos_temp = []
    
    for archivo in archivos:
        content = await archivo.read()
        total_size += len(content)
        archivos_temp.append({
            'content': content,
            'filename': archivo.filename,
            'size': len(content)
        })
    
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"El tamaño total excede el límite de {MAX_UPLOAD_SIZE_GB}GB"
        )
    
    pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
    os.makedirs(pedido_dir, exist_ok=True)
    archivos_guardados = pedido.get("archivos", [])

    for archivo_temp in archivos_temp:
        nombre = archivo_temp['filename']
        ext = os.path.splitext(nombre)[1]
        ruta = os.path.join(pedido_dir, nombre)
        
        try:
            with open(ruta, "wb") as buffer:
                buffer.write(archivo_temp['content'])
            
            archivos_guardados.append({
                "nombre": nombre,
                "ruta": ruta,
                "tipo": ext.lstrip("."),
                "tamano": archivo_temp['size']
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")

    update_data = {"archivos": archivos_guardados}
    if pedido.get("estado") == "en espera":
        update_data["estado"] = "pendiente"
    
    db_client.local.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": update_data}
    )

    pedido_actualizado = pedido_schema(
        db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"patch-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    return Pedido(**pedido_actualizado)


@router.get("/{pedido_id}/archivos")
async def descargar_todos_archivos(
    pedido_id: str,
    token: str = Depends(validar_token)
):
    pedido = db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    archivos = pedido.get("archivos", [])
    if not archivos:
        raise HTTPException(status_code=404, detail="El pedido no tiene archivos")

    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for archivo in archivos:
            ruta = archivo["ruta"]
            if os.path.exists(ruta):
                zip_file.write(ruta, arcname=archivo["nombre"])
            else:
                print(f"Advertencia: Archivo no encontrado: {ruta}")

    zip_buffer.seek(0)
    zip_size = zip_buffer.getbuffer().nbytes

    folio = pedido.get("folio", pedido_id)
    filename = f"{folio}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(zip_size)
        }
    )


@router.patch("/{pedido_id}/venta", response_model=Pedido)
async def actualizar_venta_pedido(
    pedido_id: str,
    venta_id: str = Form(...),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    resultado = db_client.local.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": {"venta_id": venta_id}}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el pedido")
    
    pedido_actualizado = pedido_schema(
        db_client.local.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"patch-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    
    return Pedido(**pedido_actualizado)
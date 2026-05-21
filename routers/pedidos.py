import shutil
import tempfile
import zipfile
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Header
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import os
import json
from core.database import db_client
from core.pedidos_archivos import (
    UPLOAD_DIR,
    eliminar_rutas,
    guardar_uploads,
    ruta_archivo_absoluta,
)
from models.pedido import Pedido
from schemas.pedido import pedido_schema, pedidos_schema
from validar_token import validar_token
from routers.websocket import manager
from fastapi.responses import FileResponse
from generador_folio import generar_folio_pedido
from starlette.background import BackgroundTask

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def _eliminar_archivo_temporal(ruta: str) -> None:
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError as e:
        print(f"Advertencia: No se pudo eliminar ZIP temporal {ruta}: {str(e)}")


def _nombre_unico_zip(nombre: str, usados: set[str]) -> str:
    candidato = nombre
    contador = 1
    stem, ext = os.path.splitext(nombre)
    while candidato.lower() in usados:
        candidato = f"{stem}_{contador}{ext}"
        contador += 1
    usados.add(candidato.lower())
    return candidato


@router.get("/all", response_model=List[Pedido])
async def obtener_pedidos(token: str = Depends(validar_token)):
    pedidos = db_client.pbstation.pedidos.find(
        {"estado": {"$ne": "entregado"}}
    ).sort("fecha", 1)
    return pedidos_schema(pedidos)

@router.get("/historial")
async def obtener_pedidos_historial(
    page: int = 1,
    page_size: int = 60,
    sucursal_id: str = None,
    token: str = Depends(validar_token)
):
    filtros = {"$or": [{"estado": "entregado"}, {"cancelado": True}]}
    if sucursal_id:
        filtros["sucursal_id"] = sucursal_id
    total = db_client.pbstation.pedidos.count_documents(filtros)
    skip = (page - 1) * page_size
    pedidos = db_client.pbstation.pedidos.find(filtros)\
        .sort("fecha_entregado", -1)\
        .skip(skip)\
        .limit(page_size)
    total_pages = (total + page_size - 1) // page_size
    return {
        "data": pedidos_schema(pedidos),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@router.get("/by-venta-folio/{venta_folio}", response_model=Pedido)
async def obtener_pedido_por_venta_folio(venta_folio: str, token: str = Depends(validar_token)):
    pedido = db_client.pbstation.pedidos.find_one({"venta_folio": venta_folio})
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado para el folio de venta proporcionado")
    
    return Pedido(**pedido_schema(pedido))

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
    if not archivos and estado != 'enEspera':
        raise HTTPException(
            status_code=400,
            detail="Los pedidos deben tener archivos o estar en estado 'en espera'"
        )
    
    folio = generar_folio_pedido(db_client.pbstation, pedido_data['sucursal_id'])

    pedido_temp = {
        "cliente_id": pedido_data['cliente_id'],
        "usuario_id": pedido_data['usuario_id'],
        "usuario_id_entrego": None,
        "sucursal_id": pedido_data['sucursal_id'],
        "venta_id": pedido_data.get('venta_id', ''),
        "venta_folio": pedido_data.get('venta_folio', ''),
        "folio": folio,
        "descripcion": pedido_data.get('descripcion', ''),
        "fecha": datetime.fromisoformat(pedido_data['fecha']),
        "fecha_entrega": datetime.fromisoformat(pedido_data['fecha_entrega']),
        "fecha_entregado": None,
        "archivos": [],
        "estado": estado,
        "cancelado": False,        
    }

    result = db_client.pbstation.pedidos.insert_one(pedido_temp)
    pedido_id = str(result.inserted_id)

    if archivos:
        try:
            archivos_guardados = await guardar_uploads(pedido_id, archivos)
        except Exception:
            pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
            if os.path.exists(pedido_dir):
                shutil.rmtree(pedido_dir)
            db_client.pbstation.pedidos.delete_one({"_id": ObjectId(pedido_id)})
            raise
        db_client.pbstation.pedidos.update_one(
            {"_id": ObjectId(pedido_id)},
            {"$push": {"archivos": {"$each": archivos_guardados}}}
        )

    nuevo_pedido = pedido_schema(db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)}))
    await manager.broadcast(f"post-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    return Pedido(**nuevo_pedido)

@router.patch("/{pedido_id}/archivos", response_model=Pedido)
async def agregar_archivos_pedido(
    pedido_id: str,
    archivos: List[UploadFile] = File(...),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    archivos_guardados = await guardar_uploads(pedido_id, archivos)

    update_ops = {"$push": {"archivos": {"$each": archivos_guardados}}}
    if pedido.get("estado") in {"enEspera", "en espera"}:
        update_ops["$set"] = {"estado": "pendiente"}
    
    resultado = db_client.pbstation.pedidos.update_one(
        {
            "_id": ObjectId(pedido_id),
            "estado": {"$nin": ["entregado", "cancelado"]},
            "cancelado": {"$ne": True}
        },
        update_ops
    )
    if resultado.matched_count == 0:
        eliminar_rutas([archivo["ruta"] for archivo in archivos_guardados])
        raise HTTPException(status_code=409, detail="El pedido ya no acepta archivos")

    pedido_actualizado = pedido_schema(
        db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"update-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    return Pedido(**pedido_actualizado)

@router.get("/{pedido_id}/archivo/{archivo_nombre}")
async def descargar_archivo_individual(
    pedido_id: str,
    archivo_nombre: str,
    token: str = Depends(validar_token)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    archivos = pedido.get("archivos", [])
    archivo = next((a for a in archivos if a["nombre"] == archivo_nombre), None)
    
    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    ruta = ruta_archivo_absoluta(archivo["ruta"])
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado")

    return FileResponse(
        path=ruta,
        filename=archivo.get("nombre_original") or archivo["nombre"],
        media_type="application/octet-stream"
    )

@router.get("/{pedido_id}/archivos")
async def descargar_archivos_zip(
    pedido_id: str,
    token: str = Depends(validar_token)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    archivos = pedido.get("archivos", [])
    if not archivos:
        raise HTTPException(status_code=404, detail="El pedido no tiene archivos")

    folio = pedido.get("folio", pedido_id)
    filename = f"{folio}.zip"
    zip_temp = tempfile.NamedTemporaryFile(
        prefix=f"pedido_{pedido_id}_",
        suffix=".zip",
        delete=False,
    )
    zip_path = zip_temp.name
    zip_temp.close()

    try:
        nombres_usados = set()
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for archivo in archivos:
                ruta = ruta_archivo_absoluta(archivo["ruta"])
                if os.path.exists(ruta):
                    nombre_zip = _nombre_unico_zip(
                        archivo.get("nombre_original") or archivo["nombre"],
                        nombres_usados,
                    )
                    zip_file.write(ruta, arcname=nombre_zip)
                else:
                    print(f"Advertencia: Archivo no encontrado: {ruta}")
    except Exception:
        _eliminar_archivo_temporal(zip_path)
        raise

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(_eliminar_archivo_temporal, zip_path),
    )

@router.patch("/{pedido_id}/venta", response_model=Pedido)
async def confirmar_pedido(
    pedido_id: str,
    venta_id: str = Form(...),
    venta_folio: str = Form(...),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    resultado = db_client.pbstation.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": {"venta_id": venta_id, "venta_folio": venta_folio}}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el pedido")
    
    pedido_actualizado = pedido_schema(
        db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"update-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    
    return Pedido(**pedido_actualizado)

@router.patch("/{pedido_id}/estado", response_model=Pedido)
async def actualizar_estado_pedido(
    pedido_id: str,
    estado: str = Form(...),
    usuario_id_entrego: Optional[str] = Form(None),
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Validar que usuario_id_entrego sea requerido solo cuando estado es "entregado"
    if estado.lower() == "entregado" and not usuario_id_entrego:
        raise HTTPException(
            status_code=400, 
            detail="usuario_id_entrego es requerido cuando el estado es 'entregado'"
        )
    
    # Preparar datos para actualizar
    update_data = {"estado": estado}
    
    # Si el estado es "entregado", eliminar los archivos físicos y agregar usuario_id_entrego
    if estado.lower() == "entregado":
        update_data["usuario_id_entrego"] = usuario_id_entrego
        update_data["fecha_entregado"] = datetime.now()  # Agregar fecha actual
        
        pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
        try:
            if os.path.exists(pedido_dir):
                shutil.rmtree(pedido_dir)
                print(f"Archivos del pedido {pedido_id} eliminados automáticamente")
                
                # Vaciar el array de archivos en la base de datos
                update_data["archivos"] = []
        except Exception as e:
            print(f"Advertencia: No se pudieron eliminar archivos del pedido {pedido_id}: {str(e)}")
            # No lanzamos error para no interrumpir el cambio de estado
    
    # Actualizar el pedido con todos los cambios
    resultado = db_client.pbstation.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": update_data}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el pedido")
    
    pedido_actualizado = pedido_schema(
        db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"update-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    
    return Pedido(**pedido_actualizado)

@router.patch("/{pedido_id}/cancelar", response_model=Pedido)
async def cancelar_pedido(
    pedido_id: str,
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Actualizar el campo cancelado y agregar fecha_entregado
    resultado = db_client.pbstation.pedidos.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": {
            "cancelado": True,
            "estado": "cancelado",
            "fecha_entregado": datetime.now()  # Guardar fecha de cancelación
        }}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=400, detail="No se pudo cancelar el pedido")
    
    # Eliminar los archivos físicos del pedido
    pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
    try:
        if os.path.exists(pedido_dir):
            shutil.rmtree(pedido_dir)
            print(f"Archivos del pedido {pedido_id} eliminados automáticamente")
            
            # Vaciar el array de archivos en la base de datos
            db_client.pbstation.pedidos.update_one(
                {"_id": ObjectId(pedido_id)},
                {"$set": {"archivos": []}}
            )
    except Exception as e:
        print(f"Advertencia: No se pudieron eliminar archivos del pedido {pedido_id}: {str(e)}")
        # No lanzamos error para no interrumpir la cancelación
    
    pedido_actualizado = pedido_schema(
        db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    )
    
    await manager.broadcast(f"update-pedido:{pedido_id}", exclude_connection_id=x_connection_id)
    
    return Pedido(**pedido_actualizado)

@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pedido(
    pedido_id: str,
    token: str = Depends(validar_token),
    x_connection_id: Optional[str] = Header(None)
):
    # Verificar que el pedido existe
    pedido = db_client.pbstation.pedidos.find_one({"_id": ObjectId(pedido_id)})
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    # Eliminar los archivos físicos del pedido si existen
    pedido_dir = os.path.join(UPLOAD_DIR, pedido_id)
    try:
        if os.path.exists(pedido_dir):
            shutil.rmtree(pedido_dir)
            print(f"Archivos del pedido {pedido_id} eliminados exitosamente")
    except Exception as e:
        print(f"Advertencia: No se pudieron eliminar archivos del pedido {pedido_id}: {str(e)}")
        # Continuamos con la eliminación del pedido en la BD aunque falle la eliminación de archivos
    
    # Eliminar el pedido de la base de datos
    resultado = db_client.pbstation.pedidos.delete_one({"_id": ObjectId(pedido_id)})
    
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=400, detail="No se pudo eliminar el pedido")
    
    return None  # 204 No Content no devuelve body


# # prueba!!
# @router.post("/crear-pedidos-prueba", status_code=status.HTTP_201_CREATED)
# async def crear_pedidos_prueba(token: str = Depends(validar_token)):
#     """
#     Endpoint de prueba: Crea 200 pedidos con fechas incrementales y diferentes estados
#     """
#     from datetime import datetime, timedelta
#     import random
    
#     pedidos_creados = []
#     fecha_base = datetime(2025, 1, 1, 8, 0, 0)  # 1 de enero 2025, 8:00 AM
    
#     estados_posibles = ["pendiente", "en_proceso", "listo", "entregado", "cancelado"]
    
#     try:
#         for i in range(200):
#             # Incrementar 2 horas por cada pedido
#             fecha_pedido = fecha_base + timedelta(hours=2 * i)
#             # La fecha de entrega es 3-5 horas después del pedido
#             horas_entrega = random.randint(3, 5)
#             fecha_entrega = fecha_pedido + timedelta(hours=horas_entrega)
            
#             # Seleccionar estado (80% entregados, 10% pendientes, 5% en proceso, 5% listo)
#             rand = random.random()
#             if rand < 0.80:
#                 estado = "entregado"
#                 cancelado = False
#                 usuario_entrego = "682e2177ea82c26a045f21bb"
#             elif rand < 0.90:
#                 estado = "pendiente"
#                 cancelado = True
#                 usuario_entrego = None
#             elif rand < 0.95:
#                 estado = "entregado"
#                 cancelado = False
#                 usuario_entrego = "682e2177ea82c26a045f21bb"
#             elif rand < 0.98:
#                 estado = "pendiente"
#                 cancelado = True
#                 usuario_entrego = None
#             else:
#                 estado = "entregado"
#                 cancelado = False
#                 usuario_entrego = "682e2177ea82c26a045f21bb"
            
#             # Generar folio estilo "B2530409"
#             folio_numero = 2530409 + i
#             folio = f"B{folio_numero}"
            
#             # Generar folio de venta estilo "251031B10"
#             venta_folio = f"25{fecha_pedido.strftime('%m%d')}B{10 + i}"
            
#             pedido_dict = {
#                 "cliente_id": "68c05a32842ab97689a854d9",
#                 "usuario_id": "682e2177ea82c26a045f21bb",
#                 "sucursal_id": "68e3ecd2ed1d26f44deda641",
#                 "venta_id": f"venta_id_{i:05d}",  # ID ficticio de venta
#                 "venta_folio": venta_folio,
#                 "folio": folio,
#                 "descripcion": f"Pedido de prueba #{i + 1}" if i % 10 == 0 else "",
#                 "fecha": fecha_pedido,
#                 "fecha_entrega": fecha_entrega,
#                 "archivos": [],
#                 "estado": estado,
#                 "cancelado": cancelado
#             }
            
#             # Agregar usuario_id_entrego solo si está entregado
#             if usuario_entrego:
#                 pedido_dict["usuario_id_entrego"] = usuario_entrego
            
#             id_insertado = db_client.pbstation.pedidos.insert_one(pedido_dict).inserted_id
#             pedidos_creados.append({
#                 "id": str(id_insertado),
#                 "folio": folio,
#                 "estado": estado
#             })
        
#         # Contar pedidos por estado
#         conteo_estados = {}
#         for pedido in pedidos_creados:
#             estado = pedido["estado"]
#             conteo_estados[estado] = conteo_estados.get(estado, 0) + 1
        
#         return {
#             "mensaje": f"Se crearon {len(pedidos_creados)} pedidos de prueba",
#             "total": len(pedidos_creados),
#             "primera_fecha": fecha_base.isoformat(),
#             "ultima_fecha": (fecha_base + timedelta(hours=2 * 199)).isoformat(),
#             "conteo_por_estado": conteo_estados,
#             "primeros_pedidos": pedidos_creados[:5]  # Muestra solo los primeros 5
#         }
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al crear pedidos de prueba: {str(e)}"
#         )

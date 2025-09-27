from core.websocket_manager import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

# WebSocket manager
manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, sucursal_id: Optional[str] = Query(None)):
    await manager.connect(websocket, sucursal_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Aquí puedes manejar mensajes entrantes si quieres (opcional)
            print(f"Mensaje recibido de {'sucursal ' + sucursal_id if sucursal_id else 'cliente sin sucursal'}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Endpoint alternativo con sucursal en la ruta (opcional)
@router.websocket("/ws/{sucursal_id}")
async def websocket_endpoint_with_sucursal(websocket: WebSocket, sucursal_id: str):
    await manager.connect(websocket, sucursal_id)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Mensaje recibido de sucursal {sucursal_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
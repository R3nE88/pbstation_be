from core.websocket_manager import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

# WebSocket manager
manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, sucursal_id: Optional[str] = Query(None)):
    # Conectar y obtener el connection_id único generado por el manager
    connection_id = await manager.connect(websocket, sucursal_id)
    
    try:
        # IMPORTANTE: Enviar el connection_id al cliente inmediatamente
        await manager.send_personal_message(f"connection_id:{connection_id}", websocket)
        
        while True:
            data = await websocket.receive_text()
            # Aquí puedes manejar mensajes entrantes si quieres (opcional)
            print(f"Mensaje recibido de cliente {connection_id} {'(sucursal ' + sucursal_id + ')' if sucursal_id else '(sin sucursal)'}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Cliente {connection_id} desconectado")

# Endpoint alternativo con sucursal en la ruta (opcional)
@router.websocket("/ws/{sucursal_id}")
async def websocket_endpoint_with_sucursal(websocket: WebSocket, sucursal_id: str):
    # Conectar y obtener el connection_id único generado por el manager
    connection_id = await manager.connect(websocket, sucursal_id)
    
    try:
        # IMPORTANTE: Enviar el connection_id al cliente inmediatamente
        await manager.send_personal_message(f"connection_id:{connection_id}", websocket)
        
        while True:
            data = await websocket.receive_text()
            print(f"Mensaje recibido de cliente {connection_id} (sucursal {sucursal_id}): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Cliente {connection_id} desconectado de sucursal {sucursal_id}")
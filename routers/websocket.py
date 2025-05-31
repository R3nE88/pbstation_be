from core.websocket_manager import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# WebSocket manager
manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Aquí puedes manejar mensajes entrantes si quieres (opcional)
            print(f"Mensaje recibido: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
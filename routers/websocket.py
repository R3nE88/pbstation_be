from core.websocket_manager import ConnectionManager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional
from validar_token import decodificar_jwt
from core.database import db_client

# WebSocket manager
manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, sucursal_id: Optional[str] = Query(None), token: Optional[str] = Query(None)):
    if not _validar_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    # Conectar y obtener el connection_id único generado por el manager
    connection_id = await manager.connect(websocket, sucursal_id)
    
    try:
        # IMPORTANTE: Enviar el connection_id al cliente inmediatamente
        await manager.send_personal_message(f"connection_id:{connection_id}", websocket)
        
        while True:
            data = await websocket.receive_text()
            # Aquí puedes manejar mensajes entrantes si quieres (opcional)
            if data != 'ping':
                print(f"Mensaje recibido de cliente {connection_id} {'(sucursal ' + sucursal_id + ')' if sucursal_id else '(sin sucursal)'}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Cliente {connection_id} desconectado")

# Endpoint alternativo con sucursal en la ruta (opcional)
@router.websocket("/ws/{sucursal_id}")
async def websocket_endpoint_with_sucursal(websocket: WebSocket, sucursal_id: str, token: Optional[str] = Query(None)):
    if not _validar_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    # Conectar y obtener el connection_id único generado por el manager
    connection_id = await manager.connect(websocket, sucursal_id)
    
    try:
        # IMPORTANTE: Enviar el connection_id al cliente inmediatamente
        await manager.send_personal_message(f"connection_id:{connection_id}", websocket)
        
        while True:
            data = await websocket.receive_text()
            if data != 'ping':
                print(f"Mensaje recibido de cliente {connection_id} (sucursal {sucursal_id}): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Cliente {connection_id} desconectado de sucursal {sucursal_id}")

def _validar_ws_token(token: Optional[str]) -> bool:
    if not token:
        return False
    try:
        payload = decodificar_jwt(token)
        session = db_client.pbstation.sesiones.find_one({"session_id": payload.get("sid")})
        return bool(session and not session.get("revoked"))
    except Exception:
        return False

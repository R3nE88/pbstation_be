from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Mantener las conexiones generales (compatibilidad)
        self.active_connections: List[WebSocket] = []
        # Nuevas estructuras para manejar sucursales
        self.sucursal_connections: Dict[str, List[WebSocket]] = {}
        self.connection_to_sucursal: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, sucursal_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Si especifica sucursal, agregarlo al grupo
        if sucursal_id:
            if sucursal_id not in self.sucursal_connections:
                self.sucursal_connections[sucursal_id] = []
            self.sucursal_connections[sucursal_id].append(websocket)
            self.connection_to_sucursal[websocket] = sucursal_id
            print(f"Cliente conectado a sucursal {sucursal_id}. Total: {len(self.active_connections)}")
        else:
            print(f"Cliente conectado (sin sucursal). Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        # Remover de conexiones generales
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remover de grupo de sucursal si existe
        if websocket in self.connection_to_sucursal:
            sucursal_id = self.connection_to_sucursal[websocket]
            if sucursal_id in self.sucursal_connections:
                if websocket in self.sucursal_connections[sucursal_id]:
                    self.sucursal_connections[sucursal_id].remove(websocket)
                # Limpiar grupo vacío
                if not self.sucursal_connections[sucursal_id]:
                    del self.sucursal_connections[sucursal_id]
            del self.connection_to_sucursal[websocket]
            print(f"Cliente desconectado de sucursal {sucursal_id}. Total: {len(self.active_connections)}")
        else:
            print(f"Cliente desconectado. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Envía mensaje a todas las conexiones (método original)"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Conexión cerrada, marcar para remover
                disconnected.append(connection)
        
        # Limpiar conexiones cerradas
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_sucursal(self, message: str, sucursal_id: str):
        """Envía mensaje solo a conexiones de una sucursal específica"""
        if sucursal_id in self.sucursal_connections:
            disconnected = []
            for connection in self.sucursal_connections[sucursal_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Conexión cerrada, marcar para remover
                    disconnected.append(connection)
            
            # Limpiar conexiones cerradas
            for connection in disconnected:
                self.disconnect(connection)
            
            print(f"Mensaje enviado a sucursal {sucursal_id}: {message}")
        else:
            print(f"No hay conexiones para la sucursal {sucursal_id}")

    def get_sucursal_connections_count(self, sucursal_id: str) -> int:
        """Obtiene el número de conexiones activas para una sucursal"""
        return len(self.sucursal_connections.get(sucursal_id, []))

    def get_all_sucursales(self) -> List[str]:
        """Obtiene lista de todas las sucursales con conexiones activas"""
        return list(self.sucursal_connections.keys())

# from typing import List
# from fastapi import WebSocket

# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: List[WebSocket] = []

#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.append(websocket)
#         print(f"Cliente conectado. Total: {len(self.active_connections)}")

#     def disconnect(self, websocket: WebSocket):
#         if websocket in self.active_connections:
#             self.active_connections.remove(websocket)
#             print(f"Cliente desconectado. Total: {len(self.active_connections)}")

#     async def send_personal_message(self, message: str, websocket: WebSocket):
#         await websocket.send_text(message)

#     async def broadcast(self, message: str):
#         for connection in self.active_connections:
#             await connection.send_text(message)
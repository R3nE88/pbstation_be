from typing import List, Dict, Optional
from fastapi import WebSocket
import uuid

class ConnectionManager:
    def __init__(self):
        # Mantener las conexiones generales
        self.active_connections: List[WebSocket] = []
        # Estructuras para manejar sucursales
        self.sucursal_connections: Dict[str, List[WebSocket]] = {}
        self.connection_to_sucursal: Dict[WebSocket, str] = {}
        # NUEVO: Mapeo de WebSocket a ID único de conexión
        self.websocket_to_id: Dict[WebSocket, str] = {}
        self.id_to_websocket: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, sucursal_id: str = None) -> str:
        """
        Conecta un WebSocket y retorna un ID único de conexión
        """
        await websocket.accept()
        
        # Generar ID único para esta conexión
        connection_id = str(uuid.uuid4())
        
        # Guardar mapeos
        self.active_connections.append(websocket)
        self.websocket_to_id[websocket] = connection_id
        self.id_to_websocket[connection_id] = websocket
        
        # Si especifica sucursal, agregarlo al grupo
        if sucursal_id:
            if sucursal_id not in self.sucursal_connections:
                self.sucursal_connections[sucursal_id] = []
            self.sucursal_connections[sucursal_id].append(websocket)
            self.connection_to_sucursal[websocket] = sucursal_id
            print(f"Cliente {connection_id} conectado a sucursal {sucursal_id}. Total: {len(self.active_connections)}")
        else:
            print(f"Cliente {connection_id} conectado (sin sucursal). Total: {len(self.active_connections)}")
        
        return connection_id

    def disconnect(self, websocket: WebSocket):
        """
        Desconecta un WebSocket y limpia todos sus mapeos
        """
        # Obtener y remover ID de conexión
        connection_id = self.websocket_to_id.get(websocket)
        if connection_id:
            if connection_id in self.id_to_websocket:
                del self.id_to_websocket[connection_id]
            del self.websocket_to_id[websocket]
        
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
            print(f"Cliente {connection_id} desconectado de sucursal {sucursal_id}. Total: {len(self.active_connections)}")
        else:
            print(f"Cliente {connection_id} desconectado. Total: {len(self.active_connections)}")

    def get_websocket_by_connection_id(self, connection_id: str) -> Optional[WebSocket]:
        """
        Obtiene el WebSocket asociado a un connection_id
        """
        return self.id_to_websocket.get(connection_id)

    def get_connection_id(self, websocket: WebSocket) -> Optional[str]:
        """
        Obtiene el connection_id de un WebSocket
        """
        return self.websocket_to_id.get(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, exclude_connection_id: str = None):
        """
        Envía mensaje a todas las conexiones excepto la especificada por connection_id
        """
        # Obtener el WebSocket a excluir si se proporcionó un ID
        exclude_ws = None
        if exclude_connection_id:
            exclude_ws = self.id_to_websocket.get(exclude_connection_id)
        
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude_ws:
                continue  # Saltar la conexión excluida
            try:
                await connection.send_text(message)
            except:
                # Conexión cerrada, marcar para remover
                disconnected.append(connection)
        
        # Limpiar conexiones cerradas
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_sucursal(self, message: str, sucursal_id: str, exclude_connection_id: str = None):
        """
        Envía mensaje solo a conexiones de una sucursal específica, excepto la especificada por connection_id
        """
        if sucursal_id in self.sucursal_connections:
            # Obtener el WebSocket a excluir si se proporcionó un ID
            exclude_ws = None
            if exclude_connection_id:
                exclude_ws = self.id_to_websocket.get(exclude_connection_id)
            
            disconnected = []
            for connection in self.sucursal_connections[sucursal_id]:
                if connection == exclude_ws:
                    continue  # Saltar la conexión excluida
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
import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Подключить нового клиента"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Отключить клиента"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Удаляем из подписок
        for channel in list(self.subscriptions.keys()):
            if websocket in self.subscriptions[channel]:
                self.subscriptions[channel].remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Отправить личное сообщение клиенту"""
        try:
            await websocket.send_text(json.dumps(message))
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Отправить сообщение всем подключенным клиентам"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Удаляем отключенных клиентов
        for connection in disconnected:
            self.disconnect(connection)
    
    async def subscribe_to_channel(self, channel: str, websocket: WebSocket):
        """Подписать клиента на канал"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        
        if websocket not in self.subscriptions[channel]:
            self.subscriptions[channel].append(websocket)
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Отправить сообщение в канал"""
        if channel in self.subscriptions:
            disconnected = []
            
            for connection in self.subscriptions[channel]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Удаляем отключенных клиентов
            for connection in disconnected:
                if connection in self.subscriptions[channel]:
                    self.subscriptions[channel].remove(connection)
    
    def get_active_count(self) -> int:
        """Получить количество активных соединений"""
        return len(self.active_connections)

# Глобальный менеджер соединений
connection_manager = ConnectionManager()
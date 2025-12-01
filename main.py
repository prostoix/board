import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import config
from database.crud import db_manager
from database.models import MessageCreate
from message_processing.formatter import message_formatter
from websocket_manager.connection_manager import connection_manager
from rabbitmq_client.rabbitmq_handler import rabbitmq_handler

# Создаем FastAPI приложение
app = FastAPI(
    title="Message Display Server",
    description="Сервер для отображения сообщений через WebSocket и Polling",
    version="2.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация при старте
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    print("=" * 60)
    print("🚀 Запуск Message Display Server")
    print("=" * 60)
    
    # Подключаемся к RabbitMQ
    if await rabbitmq_handler.connect():
        # Запускаем consumer в фоне
        asyncio.create_task(rabbitmq_handler.consume_messages())
    
    print(f"🌐 Web интерфейс:      http://localhost:8050")
    print(f"🔌 WebSocket:          ws://localhost:{config.WEBSOCKET_PORT}/ws")
    print(f"🔄 Polling API:        http://localhost:8050/poll?last_id=0")
    print(f"📋 Messages API:       http://localhost:8050/messages?limit=20")
    print(f"🐇 RabbitMQ сервер:    {config.RABBITMQ_HOST}")
    print(f"📊 RabbitMQ очередь:   {config.RABBITMQ_QUEUE}")
    print("=" * 60)
    print("✅ Сервер запущен и готов к работе!")
    print("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении работы"""
    await rabbitmq_handler.close()
    print("👋 Сервер завершает работу")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для реального времени"""
    await connection_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Обработка служебных сообщений
            if data == "ping":
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    websocket
                )
            elif data.startswith("subscribe:"):
                channel = data.split(":")[1]
                await connection_manager.subscribe_to_channel(channel, websocket)
                await connection_manager.send_personal_message(
                    {"type": "subscribed", "channel": channel},
                    websocket
                )
                    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

# REST API endpoints
@app.get("/")
async def read_index():
    """Главная страница"""
    return FileResponse('/app/static/index.html')

@app.get("/api/messages")
async def get_recent_messages(limit: int = 20):
    """Получить последние сообщения (JSON API)"""
    messages = db_manager.get_recent_messages(limit)
    
    return {
        "messages": [
            {
                "id": msg.message_id,
                "formatted": msg.formatted_message,
                "raw": msg.message,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ],
        "last_id": db_manager.get_last_message_id(),
        "total": len(messages)
    }

@app.get("/api/poll")
async def poll_messages(last_id: int = 0):
    """Long polling endpoint для старых клиентов"""
    messages = db_manager.get_messages_since(last_id)
    
    # Если сообщений нет, ждем некоторое время (long polling)
    if not messages:
        await asyncio.sleep(config.POLLING_TIMEOUT)
        messages = db_manager.get_messages_since(last_id)
    
    return {
        "messages": [
            {
                "id": msg.message_id,
                "formatted": msg.formatted_message,
                "raw": msg.message,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ],
        "last_id": db_manager.get_last_message_id(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/last")
async def get_last_message_api():
    """Получить последнее сообщение"""
    last_message = db_manager.get_last_message()
    
    if not last_message:
        return {
            "message": "No messages yet",
            "id": 0
        }
    
    return {
        "id": last_message.message_id,
        "formatted": last_message.formatted_message,
        "raw": last_message.message,
        "timestamp": last_message.timestamp.isoformat()
    }

@app.post("/api/messages")
async def create_message(message: dict):
    """Создать новое сообщение (для тестирования)"""
    if "message" not in message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    message_text = message["message"]
    formatted = message_formatter.format_message(message_text)
    
    # Получаем новый ID
    new_id = db_manager.get_last_message_id() + 1
    
    # Создаем сообщение
    message_data = MessageCreate(
        message=message_text,
        formatted_message=formatted,
        message_id=new_id
    )
    
    saved_message = db_manager.create_message(message_data)
    
    # Отправляем через WebSocket
    await connection_manager.broadcast({
        "id": saved_message.message_id,
        "formatted": saved_message.formatted_message,
        "raw": saved_message.message,
        "timestamp": saved_message.timestamp.isoformat()
    })
    
    return {
        "id": saved_message.message_id,
        "status": "created",
        "timestamp": saved_message.timestamp.isoformat()
    }

@app.get("/api/status")
async def get_status():
    """Получить статус сервера"""
    return {
        "status": "running",
        "websocket_connections": connection_manager.get_active_count(),
        "rabbitmq_connected": rabbitmq_handler.is_connected,
        "last_message_id": db_manager.get_last_message_id(),
        "timestamp": datetime.now().isoformat()
    }

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# Для обратной совместимости
@app.get("/messages")
async def get_messages_legacy(limit: int = 20):
    """Legacy endpoint для обратной совместимости"""
    return await get_recent_messages(limit)

@app.get("/poll")
async def poll_legacy(last_id: int = 0):
    """Legacy polling endpoint"""
    return await poll_messages(last_id)

@app.get("/last")
async def last_legacy():
    """Legacy last message endpoint"""
    return await get_last_message_api()
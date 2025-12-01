import asyncio
import json
import aio_pika
from typing import Optional
from config import config
from database.crud import db_manager
from database.models import MessageCreate
from message_processing.formatter import message_formatter
from websocket_manager.connection_manager import connection_manager

class RabbitMQHandler:
    """Обработчик RabbitMQ"""
    
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.is_connected = False
        self.last_message_id = 0
    
    async def connect(self) -> bool:
        """Подключиться к RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(
                config.rabbitmq_connection_string
            )
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(config.RABBITMQ_QUEUE, durable=True)
            
            self.is_connected = True
            print(f"✅ Подключен к RabbitMQ: {config.RABBITMQ_HOST}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения к RabbitMQ: {e}")
            self.is_connected = False
            return False
    
    async def consume_messages(self):
        """Потреблять сообщения из RabbitMQ"""
        if not self.is_connected or not self.channel:
            print("⚠️ Не подключен к RabbitMQ")
            return
        
        try:
            queue = await self.channel.declare_queue(config.RABBITMQ_QUEUE, durable=True)
            
            async for message in queue:
                async with message.process():
                    message_text = message.body.decode()
                    print(f"📥 Получено из RabbitMQ: {message_text[:100]}...")
                    
                    await self.process_message(message_text)
                    
        except Exception as e:
            print(f"❌ Ошибка потребления сообщений: {e}")
            self.is_connected = False
    
    async def process_message(self, message_text: str):
        """Обработать сообщение из RabbitMQ"""
        try:
            # Получаем последний ID
            self.last_message_id = db_manager.get_last_message_id()
            new_message_id = self.last_message_id + 1
            
            # Форматируем сообщение
            formatted_message = message_formatter.format_message(message_text)
            
            # Создаем объект сообщения
            message_data = MessageCreate(
                message=message_text,
                formatted_message=formatted_message,
                message_id=new_message_id
            )
            
            # Сохраняем в базу данных
            saved_message = db_manager.create_message(message_data)
            
            # Отправляем через WebSocket
            await connection_manager.broadcast({
                "id": saved_message.message_id,
                "formatted": saved_message.formatted_message,
                "raw": saved_message.message,
                "timestamp": saved_message.timestamp.isoformat()
            })
            
            print(f"✅ Сообщение #{new_message_id} обработано")
            
        except Exception as e:
            print(f"❌ Ошибка обработки сообщения: {e}")
    
    async def publish_message(self, message: str) -> bool:
        """Опубликовать сообщение в RabbitMQ"""
        if not self.is_connected or not self.channel:
            return False
        
        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=message.encode()),
                routing_key=config.RABBITMQ_QUEUE
            )
            return True
            
        except Exception as e:
            print(f"❌ Ошибка публикации в RabbitMQ: {e}")
            return False
    
    async def close(self):
        """Закрыть соединение"""
        if self.connection:
            await self.connection.close()
            self.is_connected = False
            print("🔌 Соединение с RabbitMQ закрыто")

# Глобальный обработчик RabbitMQ
rabbitmq_handler = RabbitMQHandler()
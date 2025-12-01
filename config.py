import os
from typing import Optional

class Config:
    """Конфигурация приложения"""
    
    # RabbitMQ
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "192.168.1.137")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_QUEUE: str = os.getenv("RABBITMQ_QUEUE", "websocket_messages")
    
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "/app/messages.db")
    
    # WebSocket
    WEBSOCKET_HOST: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "8000"))
    
    # Приложение
    MAX_MESSAGES_HISTORY: int = 100
    POLLING_TIMEOUT: int = 5  # секунд
    
    @property
    def rabbitmq_connection_string(self) -> str:
        """Строка подключения к RabbitMQ"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
    
config = Config()
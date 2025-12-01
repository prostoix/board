from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MessageBase(BaseModel):
    """Базовая модель сообщения"""
    message: str
    formatted_message: Optional[str] = None
    message_id: int

class MessageCreate(MessageBase):
    """Модель для создания сообщения"""
    pass

class Message(MessageBase):
    """Модель сообщения"""
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True
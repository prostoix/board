import sqlite3
from typing import List, Optional
from datetime import datetime
from .models import Message, MessageCreate
from config import config

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_path: str = config.DATABASE_URL):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Инициализировать базу данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                formatted_message TEXT,
                message_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_id ON messages(message_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)')
        conn.commit()
        conn.close()
    
    def get_last_message_id(self) -> int:
        """Получить последний ID сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(message_id) FROM messages')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0
    
    def create_message(self, message: MessageCreate) -> Message:
        """Создать новое сообщение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (message, formatted_message, message_id) 
            VALUES (?, ?, ?)
        ''', (message.message, message.formatted_message, message.message_id))
        
        message_id = cursor.lastrowid
        conn.commit()
        
        # Получаем созданное сообщение
        cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
        result = cursor.fetchone()
        conn.close()
        
        return self._row_to_message(result)
    
    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Получить сообщение по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
        result = cursor.fetchone()
        conn.close()
        
        return self._row_to_message(result) if result else None
    
    def get_messages_since(self, last_id: int) -> List[Message]:
        """Получить сообщения начиная с определенного ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages 
            WHERE message_id > ? 
            ORDER BY message_id ASC
        ''', (last_id,))
        results = cursor.fetchall()
        conn.close()
        
        return [self._row_to_message(row) for row in results]
    
    def get_recent_messages(self, limit: int = 20) -> List[Message]:
        """Получить последние сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages 
            ORDER BY message_id DESC LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        
        # Восстанавливаем порядок
        return [self._row_to_message(row) for row in reversed(results)]
    
    def get_last_message(self) -> Optional[Message]:
        """Получить последнее сообщение"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        return self._row_to_message(result) if result else None
    
    def _row_to_message(self, row) -> Message:
        """Преобразовать строку базы данных в объект Message"""
        return Message(
            id=row['id'],
            message=row['message'],
            formatted_message=row['formatted_message'],
            message_id=row['message_id'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else datetime.now()
        )

# Синглтон экземпляр базы данных
db_manager = DatabaseManager()
import sqlite3
import os
import json
import asyncio
import aio_pika
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Конфигурация RabbitMQ
RABBITMQ_HOST = "192.168.1.137"
RABBITMQ_QUEUE = "to_board"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('/app/messages.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Получить последнее сообщение
def get_last_message():
    conn = sqlite3.connect('/app/messages.db')
    cursor = conn.cursor()
    cursor.execute('SELECT message FROM messages ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "No messages yet"

# Сохранить сообщение
def save_message(message):
    conn = sqlite3.connect('/app/messages.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (message) VALUES (?)', (message,))
    conn.commit()
    conn.close()

# WebSocket соединения
active_connections = []

# RabbitMQ connection
rabbit_connection = None
rabbit_channel = None

async def connect_rabbitmq():
    global rabbit_connection, rabbit_channel
    try:
        rabbit_connection = await aio_pika.connect_robust(
            f"amqp://guest:guest@{RABBITMQ_HOST}/"
        )
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.declare_queue(RABBITMQ_QUEUE, durable=True)
        print("Connected to RabbitMQ")
    except Exception as e:
        print(f"RabbitMQ connection error: {e}")

async def consume_rabbitmq():
    try:
        queue = await rabbit_channel.declare_queue(RABBITMQ_QUEUE, durable=True)
        
        async for message in queue:
            async with message.process():
                message_text = message.body.decode()
                print(f"Received from RabbitMQ: {message_text}")
                
                # Сохраняем в БД
                save_message(message_text)
                
                # Отправляем всем WebSocket клиентам
                for connection in active_connections:
                    try:
                        await connection.send_text(message_text)
                    except:
                        active_connections.remove(connection)
    except Exception as e:
        print(f"RabbitMQ consume error: {e}")

async def publish_to_rabbitmq(message: str):
    try:
        if rabbit_channel:
            await rabbit_channel.default_exchange.publish(
                aio_pika.Message(body=message.encode()),
                routing_key=RABBITMQ_QUEUE
            )
            return True
    except Exception as e:
        print(f"RabbitMQ publish error: {e}")
    return False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = data.strip()
            
            if message:
                # Сохраняем сообщение в БД
                save_message(message)
                
                # Публикуем в RabbitMQ
                await publish_to_rabbitmq(message)
                
                # Рассылаем всем подключенным клиентам
                for connection in active_connections:
                    try:
                        await connection.send_text(message)
                    except:
                        active_connections.remove(connection)
                    
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/last-message")
async def get_last_message_api():
    return {"message": get_last_message()}

@app.get("/")
async def read_index():
    return FileResponse('/app/static/index.html')

# HTML страница (адаптированная для мобильных)
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Messages</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { 
            margin: 0;
            padding: 0;
            background-color: #000000;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            font-size: 14px;
        }
        
        .container {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-height: -webkit-fill-available;
        }
        
        .header {
            padding: 10px 15px;
            background: #111;
            border-bottom: 1px solid #333;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .status {
            color: #666;
        }
        
        .status.connected {
            color: #00ff00;
        }
        
        #messages { 
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            overflow-x: hidden;
            border: none;
            line-height: 1.4;
            -webkit-overflow-scrolling: touch;
        }
        
        .input-container {
            padding: 15px;
            border-top: 1px solid #333;
            background: #111;
        }
        
        #messageInput { 
            width: 100%;
            padding: 12px;
            background: #000;
            color: #00ff00;
            border: 1px solid #333;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            outline: none;
            border-radius: 0;
            -webkit-appearance: none;
        }
        
        #messageInput:focus {
            border-color: #00ff00;
        }
        
        .message {
            margin: 8px 0;
            padding: 10px;
            border-left: 2px solid #00ff00;
            background: #111;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        .system-message {
            color: #666;
            border-left-color: #666;
            font-style: italic;
        }
        
        .timestamp {
            color: #666;
            font-size: 11px;
            margin-right: 8px;
        }
        
        /* Мобильная оптимизация */
        @media (max-width: 768px) {
            body {
                font-size: 12px;
            }
            
            .header {
                padding: 8px 12px;
                font-size: 11px;
            }
            
            #messages {
                padding: 8px;
            }
            
            .input-container {
                padding: 12px;
            }
            
            #messageInput {
                padding: 10px;
                font-size: 14px;
            }
            
            .message {
                margin: 6px 0;
                padding: 8px;
            }
        }
        
        /* Портретная ориентация */
        @media (max-width: 480px) and (orientation: portrait) {
            .container {
                height: 100vh;
            }
        }
        
        /* Ландшафтная ориентация */
        @media (max-width: 850px) and (orientation: landscape) {
            .header {
                padding: 5px 10px;
                font-size: 10px;
            }
            
            #messages {
                padding: 5px;
            }
            
            .message {
                margin: 3px 0;
                padding: 5px;
            }
        }
        
        /* Скроллбар для WebKit */
        #messages::-webkit-scrollbar {
            width: 4px;
        }
        
        #messages::-webkit-scrollbar-track {
            background: #000;
        }
        
        #messages::-webkit-scrollbar-thumb {
            background: #333;
        }
        
        #messages::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>WebSocket Messages</div>
            <div id="status" class="status">Connecting...</div>
        </div>
        
        <div id="messages"></div>
        
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Type message and press Enter..." autocomplete="off">
        </div>
    </div>

    <script>
        let socket = null;
        let isConnected = false;

        function connect() {
            socket = new WebSocket("ws://" + window.location.host + "/ws");
            
            socket.onopen = function(e) {
                isConnected = true;
                updateStatus("CONNECTED", true);
                addSystemMessage("Connected to server");
                loadLastMessage();
            };
            
            socket.onmessage = function(event) {
                const message = event.data;
                addMessage(message);
            };
            
            socket.onclose = function(event) {
                isConnected = false;
                updateStatus("DISCONNECTED", false);
                addSystemMessage("Disconnected from server");
                setTimeout(connect, 3000);
            };
            
            socket.onerror = function(error) {
                updateStatus("ERROR", false);
                addSystemMessage("Connection error");
            };
        }

        function updateStatus(text, connected) {
            const statusElement = document.getElementById("status");
            statusElement.textContent = text;
            statusElement.className = "status" + (connected ? " connected" : "");
        }

        function addMessage(message) {
            const messagesDiv = document.getElementById("messages");
            const messageElement = document.createElement("div");
            messageElement.className = "message";
            
            const timestamp = new Date().toLocaleTimeString();
            messageElement.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${escapeHtml(message)}`;
            
            messagesDiv.appendChild(messageElement);
            scrollToBottom();
        }

        function addSystemMessage(message) {
            const messagesDiv = document.getElementById("messages");
            const messageElement = document.createElement("div");
            messageElement.className = "message system-message";
            messageElement.innerHTML = `[SYSTEM] ${message}`;
            
            messagesDiv.appendChild(messageElement);
            scrollToBottom();
        }

        function scrollToBottom() {
            const messagesDiv = document.getElementById("messages");
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function sendMessage() {
            const input = document.getElementById("messageInput");
            const message = input.value.trim();
            
            if (message) {
                if (isConnected) {
                    socket.send(message);
                    input.value = "";
                } else {
                    addSystemMessage("Not connected to server");
                }
            }
        }

        async function loadLastMessage() {
            try {
                const response = await fetch("/last-message");
                const data = await response.json();
                if (data.message && data.message !== "No messages yet") {
                    addSystemMessage("Last message: " + data.message);
                }
            } catch (error) {
                console.error("Error loading last message:", error);
            }
        }

        // Обработчики событий
        document.getElementById("messageInput").addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });

        // Предотвращаем zoom на двойной тап
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function (event) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        // Автофокус на поле ввода
        document.getElementById("messageInput").focus();

        // Запускаем соединение
        connect();

        // Обработка изменения ориентации
        window.addEventListener('orientationchange', function() {
            setTimeout(scrollToBottom, 100);
        });
    </script>
</body>
</html>
"""

# Создаем статическую директорию и HTML файл
if not os.path.exists("static"):
    os.makedirs("static")

with open("static/index.html", "w") as f:
    f.write(html_content)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# Инициализация БД при запуске
@app.on_event("startup")
async def startup_event():
    init_db()
    await connect_rabbitmq()
    
    # Запускаем consumer RabbitMQ в фоне
    if rabbit_channel:
        asyncio.create_task(consume_rabbitmq())
    
    print("WebSocket server started")
    print("WebSocket URL: ws://localhost:8050/ws")
    print("Web interface: http://localhost:8050")
    print(f"RabbitMQ: {RABBITMQ_HOST}")
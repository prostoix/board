import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

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

# HTML страница
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Messages</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            text-align: center;
        }
        #lastMessage { 
            border: 2px solid #4CAF50;
            padding: 20px;
            margin: 20px 0;
            background-color: #f9f9f9;
            border-radius: 5px;
            font-size: 18px;
            font-weight: bold;
        }
        #messages { 
            border: 1px solid #ddd; 
            padding: 20px; 
            min-height: 200px; 
            margin: 20px 0;
            border-radius: 5px;
            background-color: #fafafa;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }
        #messageInput { 
            flex: 1;
            padding: 12px; 
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button { 
            padding: 12px 24px; 
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .message {
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-left: 4px solid #4CAF50;
            border-radius: 3px;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            text-align: center;
        }
        .connected {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .disconnected {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebSocket Message Display</h1>
        
        <div id="status" class="status"></div>
        
        <h3>📨 Last Received Message:</h3>
        <div id="lastMessage">Loading...</div>
        
        <h3>📝 All Messages:</h3>
        <div id="messages"></div>
        
        <div class="input-group">
            <input type="text" id="messageInput" placeholder="Type your message here...">
            <button onclick="sendMessage()">Send Message</button>
        </div>
    </div>

    <script>
        let socket = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;

        function connect() {
            socket = new WebSocket("ws://" + window.location.host + "/ws");
            
            socket.onopen = function(e) {
                console.log("WebSocket connected");
                updateStatus("Connected", "connected");
                reconnectAttempts = 0;
                loadLastMessage();
            };
            
            socket.onmessage = function(event) {
                const message = event.data;
                // Обновляем последнее сообщение
                document.getElementById("lastMessage").innerText = message;
                
                // Добавляем в список сообщений
                const messagesDiv = document.getElementById("messages");
                const messageElement = document.createElement("div");
                messageElement.className = "message";
                messageElement.innerHTML = `<strong>${new Date().toLocaleString()}:</strong> ${message}`;
                messagesDiv.appendChild(messageElement);
                
                // Прокручиваем вниз
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            };
            
            socket.onclose = function(event) {
                console.log("WebSocket disconnected");
                updateStatus("Disconnected - Attempting to reconnect...", "disconnected");
                
                if (reconnectAttempts < maxReconnectAttempts) {
                    setTimeout(() => {
                        reconnectAttempts++;
                        connect();
                    }, 2000);
                }
            };
            
            socket.onerror = function(error) {
                console.error("WebSocket error:", error);
                updateStatus("Connection error", "disconnected");
            };
        }

        function updateStatus(text, className) {
            const statusDiv = document.getElementById("status");
            statusDiv.textContent = text;
            statusDiv.className = "status " + className;
        }

        function sendMessage() {
            const input = document.getElementById("messageInput");
            const message = input.value.trim();
            
            if (message && socket && socket.readyState === WebSocket.OPEN) {
                socket.send(message);
                input.value = "";
            } else {
                alert("Not connected to server");
            }
        }

        async function loadLastMessage() {
            try {
                const response = await fetch("/last-message");
                const data = await response.json();
                document.getElementById("lastMessage").innerText = data.message;
            } catch (error) {
                console.error("Error loading last message:", error);
            }
        }

        // Обработчик нажатия Enter
        document.getElementById("messageInput").addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });

        // Автофокус на поле ввода
        document.getElementById("messageInput").focus();

        // Запускаем соединение
        connect();
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
    print("WebSocket server started on http://0.0.0.0:8050")
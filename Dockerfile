FROM python:3.9-slim

# Устанавливаем nginx и необходимые пакеты
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY app.py .
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директорию для статических файлов
RUN mkdir -p /app/static

# Создаем HTML страницу
RUN echo '<!DOCTYPE html>\
<html>\
<head>\
    <title>WebSocket Messages</title>\
    <style>\
        body { font-family: Arial, sans-serif; margin: 40px; }\
        #lastMessage { border: 2px solid #4CAF50; padding: 20px; margin: 20px 0; font-weight: bold; }\
        #messages { border: 1px solid #ccc; padding: 20px; min-height: 200px; margin: 20px 0; }\
        #messageInput { width: 300px; padding: 10px; }\
        button { padding: 10px 20px; margin-left: 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }\
        .message { margin: 5px 0; padding: 5px; background: #f9f9f9; }\
    </style>\
</head>\
<body>\
    <h1>WebSocket Message Display</h1>\
    <h3>Last Message:</h3>\
    <div id="lastMessage">Loading...</div>\
    <h3>All Messages:</h3>\
    <div id="messages"></div>\
    <div>\
        <input type="text" id="messageInput" placeholder="Enter your message">\
        <button onclick="sendMessage()">Send</button>\
    </div>\
    <script>\
        let socket = new WebSocket("ws://" + window.location.host + "/ws");\
        \
        socket.onopen = function(e) {\
            console.log("WebSocket connected");\
            loadLastMessage();\
        };\
        \
        socket.onmessage = function(event) {\
            const message = event.data;\
            document.getElementById("lastMessage").innerText = message;\
            \
            const messagesDiv = document.getElementById("messages");\
            const messageElement = document.createElement("div");\
            messageElement.className = "message";\
            messageElement.innerHTML = `<strong>${new Date().toLocaleString()}:</strong> ${message}`;\
            messagesDiv.appendChild(messageElement);\
        };\
        \
        socket.onclose = function(event) {\
            console.log("WebSocket disconnected");\
        };\
        \
        function sendMessage() {\
            const input = document.getElementById("messageInput");\
            const message = input.value.trim();\
            if (message) {\
                socket.send(message);\
                input.value = "";\
            }\
        }\
        \
        async function loadLastMessage() {\
            try {\
                const response = await fetch("/last-message");\
                const data = await response.json();\
                document.getElementById("lastMessage").innerText = data.message;\
            } catch (error) {\
                console.error("Error:", error);\
            }\
        }\
        \
        document.getElementById("messageInput").addEventListener("keypress", function(e) {\
            if (e.key === "Enter") {\
                sendMessage();\
            }\
        });\
    </script>\
</body>\
</html>' > /app/static/index.html

# Открываем порты
EXPOSE 8050

# Запускаем nginx и наше приложение
CMD service nginx start && uvicorn app:app --host 0.0.0.0 --port 8000 --reload
FROM python:3.9-slim

# Устанавливаем nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаем структуру директорий
RUN mkdir -p /app/static
RUN mkdir -p /app/database
RUN mkdir -p /app/message_processing
RUN mkdir -p /app/websocket_manager
RUN mkdir -p /app/rabbitmq_client

# Копируем файлы приложения
COPY main.py .
COPY config.py .
COPY nginx.conf /etc/nginx/nginx.conf

# Копируем модули с init файлами
COPY database/ /app/database/
COPY message_processing/ /app/message_processing/
COPY websocket_manager/ /app/websocket_manager/
COPY rabbitmq_client/ /app/rabbitmq_client/

# Копируем HTML страницу
COPY static/ /app/static/

EXPOSE 8050

CMD service nginx start && uvicorn main:app --host 0.0.0.0 --port 8000
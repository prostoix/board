FROM python:3.9-slim

# Устанавливаем nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы
COPY app.py .
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем статическую директорию
RUN mkdir -p /app/static

EXPOSE 8050

CMD service nginx start && uvicorn app:app --host 0.0.0.0 --port 8000
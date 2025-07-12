# Файл: api/proxy.py (или ваш путь на Vercel)
import os
import requests
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Получаем переменные окружения
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        PROXY_AUTH_TOKEN = os.environ.get("PROXY_AUTH_TOKEN")
        
        # 2. Проверка нашего токена авторизации
        auth_header = self.headers.get("Authorization", "")
        if auth_header != f"Bearer {PROXY_AUTH_TOKEN}":
            self.send_response(403)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode('utf-8'))
            return

        # 3. Извлекаем название модели из URL
        # Ожидаем, что запрос придет на /api/proxy?model=gemini-2.5-flash
        query_components = parse_qs(urlparse(self.path).query)
        model_name = query_components.get("model", [None])[0]

        if not model_name:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Model name not specified in query parameters"}).encode('utf-8'))
            return

        # 4. Читаем тело запроса, которое прислал наш клиент
        # Мы не анализируем его, а просто передаем дальше
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        
        # 5. Формируем URL для Google API и делаем запрос
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            # Отправляем запрос в Google, используя тело от нашего клиента
            # Важно: используем `data=post_body`, а не `json=...`, чтобы передать байты "как есть"
            response = requests.post(
                api_url, 
                headers={'Content-Type': 'application/json'},
                data=post_body
            )
            response.raise_for_status()  # Вызовет исключение для плохих ответов (4xx, 5xx)
            
            # 6. Отправляем успешный ответ от Google обратно нашему клиенту
            self.send_response(response.status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.content) # Используем .content для передачи в исходном виде

        except requests.exceptions.RequestException as e:
            # В случае ошибки сети или плохого ответа от Google, сообщаем об этом
            error_message = str(e)
            status_code = 502 # Bad Gateway

            # Попытаемся извлечь оригинальный код ошибки и сообщение от Google
            if e.response is not None:
                status_code = e.response.status_code
                error_message = e.response.text

            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Failed to proxy request to Gemini", "details": error_message}).encode('utf-8'))
        
        return

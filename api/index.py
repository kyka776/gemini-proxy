import os
import requests
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Получаем ключи и пароль из настроек Vercel
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        PROXY_AUTH_TOKEN = os.environ.get("PROXY_AUTH_TOKEN")
        
        # 2. Проверка безопасности
        auth_header = self.headers.get("Authorization", "")
        if auth_header != f"Bearer {PROXY_AUTH_TOKEN}":
            self.send_response(403)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        # 3. Получаем промпт от пользователя
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        request_json = json.loads(post_body)
        
        prompt = request_json.get("prompt")
        model = request_json.get("model", "gemini-1.5-flash")

        # 4. Делаем запрос к Gemini
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response.json()).encode('utf-8'))

        except requests.exceptions.RequestException as e:
            # Отправляем ошибку
            self.send_response(502)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))
        
        return
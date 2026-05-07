import http.server
import socketserver
import json
import sqlite3
import yt_dlp
import uuid
import os
from urllib.parse import urlparse, parse_qs

# --- DATABASE SETUP ---
# रेंडर के लिए डेटाबेस पाथ सेट करना
DB_PATH = "mi_downloader.db"

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, username TEXT, api_key TEXT UNIQUE)''')
    conn.commit()
    conn.close()

setup_db()

class KushagraEngineHandler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*") # ताकि कोई भी इसे एक्सेस कर सके
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=4).encode())

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)

        # 1. Main UI (index.html)
        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            try:
                with open("index.html", "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_json({"error": "index.html not found on server"}, 404)
            return

        # 2. API: Register User
        elif parsed_path.path == "/api/register":
            name = query.get("name", [None])[0]
            if not name:
                self.send_json({"error": "Please provide a name!"}, 400)
                return
            
            new_key = f"kushagra_{str(uuid.uuid4())[:8]}"

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, api_key) VALUES (?, ?)", (name, new_key))
                conn.commit()
                conn.close()
                self.send_json({"message": f"Welcome {name}!", "your_api_key": new_key})
            except Exception as e:
                self.send_json({"error": "Database error or user already exists"}, 500)

        # 3. API: Video Engine
        elif parsed_path.path == "/api/engine":
            key = query.get("key", [None])[0]
            video_url = query.get("url", [None])[0]

            if not key or not video_url:
                self.send_json({"error": "Missing key or url"}, 400)
                return

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE api_key=?", (key,))
            user = cursor.fetchone()
            conn.close()

            if not user:
                self.send_json({"error": "Invalid API Key!"}, 401)
                return

            try:
                # Engine logic
                ydl_opts = {'format': 'best', 'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                
                self.send_json({
                    "status": "success",
                    "engine": "Kushagra Engine V3",
                    "authorized_user": user[0],
                    "title": info.get('title'),
                    "download_url": info.get('url'),
                    "thumbnail": info.get('thumbnail')
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        else:
            # बाकी Static files (CSS/JS) के लिए
            super().do_GET()

# --- RENDER PORT LOGIC ---
# Render environment variable से पोर्ट उठाता है
PORT = int(os.environ.get("PORT", 8000))

with socketserver.TCPServer(("", PORT), KushagraEngineHandler) as httpd:
    print(f"🚀 Kushagra Engine is LIVE on Port: {PORT}")
    httpd.serve_forever()
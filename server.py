import http.server
import socketserver
import json
import sqlite3
import yt_dlp
import uuid
import os
from urllib.parse import urlparse, parse_qs

# --- DATABASE SETUP ---
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
        self.send_header("Access-Control-Allow-Origin", "*") 
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=4).encode())

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)

        # 1. Main UI
        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            try:
                with open("index.html", "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_json({"error": "index.html not found"}, 404)
            return

        # 2. API: Register
        elif parsed_path.path == "/api/register":
            name = query.get("name", [None])[0]
            if not name:
                self.send_json({"error": "Name please!"}, 400)
                return
            new_key = f"kushagra_{str(uuid.uuid4())[:8]}"
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO users (username, api_key) VALUES (?, ?)", (name, new_key))
                conn.commit()
                conn.close()
                self.send_json({"your_api_key": new_key})
            except:
                self.send_json({"error": "DB Error"}, 500)

        # 3. API: Video Engine (COOKIES FIX)
        elif parsed_path.path == "/api/engine":
            key = query.get("key", [None])[0]
            video_url = query.get("url", [None])[0]

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT username FROM users WHERE api_key=?", (key,))
            user = c.fetchone()
            conn.close()

            if not user:
                self.send_json({"error": "Invalid Key"}, 401)
                return

            try:
                # GitHub par upload ki gayi cookies.txt ko read karna
                cookie_data = ""
                if os.path.exists('cookies.txt'):
                    with open('cookies.txt', 'r') as f:
                        cookie_data = f.read().strip()

                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'http_headers': {
                        'Cookie': cookie_data,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    },
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web', 'ios'],
                        }
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                
                self.send_json({
                    "status": "success",
                    "title": info.get('title'),
                    "download_url": info.get('url'),
                    "thumbnail": info.get('thumbnail')
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        else:
            super().do_GET()

# Render Port setup
PORT = int(os.environ.get("PORT", 8000))
with socketserver.TCPServer(("0.0.0.0", PORT), KushagraEngineHandler) as httpd:
    print(f"🚀 Kushagra Engine LIVE on Port: {PORT}")
    httpd.serve_forever()

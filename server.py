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
                self.send_json({"error": "Name required!"}, 400)
                return
            new_key = f"kushagra_{str(uuid.uuid4())[:8]}"
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO users (username, api_key) VALUES (?, ?)", (name, new_key))
                conn.commit()
                conn.close()
                self.send_json({"message": f"Welcome {name}!", "your_api_key": new_key})
            except:
                self.send_json({"error": "Database error"}, 500)

        # 3. API: Video Engine (ULTIMATE FIX)
        elif parsed_path.path == "/api/engine":
            key = query.get("key", [None])[0]
            video_url = query.get("url", [None])[0]

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT username FROM users WHERE api_key=?", (key,))
            user = c.fetchone()
            conn.close()

            if not user:
                self.send_json({"error": "Invalid API Key!"}, 401)
                return

            try:
                # कुकीज़ फाइल को सुरक्षित रूप से पढ़ना
                cookie_content = ""
                if os.path.exists('cookies.txt'):
                    with open('cookies.txt', 'r') as f:
                        cookie_content = f.read().strip()

                # yt-dlp के लिए सबसे एडवांस सेटिंग्स
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'ignoreerrors': True,
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                    },
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios', 'web'],
                            'player_skip': ['webpage', 'configs'],
                        }
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    
                if not info:
                    raise Exception("Could not extract video info. YouTube might be blocking this IP.")

                self.send_json({
                    "status": "success",
                    "engine": "Kushagra Engine V3 - Ultra",
                    "authorized_user": user[0],
                    "title": info.get('title'),
                    "download_url": info.get('url'),
                    "thumbnail": info.get('thumbnail'),
                    "duration": info.get('duration')
                })
            except Exception as e:
                self.send_json({"error": f"Engine Error: {str(e)}"}, 500)

        else:
            super().do_GET()

# Render Port setup
PORT = int(os.environ.get("PORT", 8000))
with socketserver.TCPServer(("0.0.0.0", PORT), KushagraEngineHandler) as httpd:
    print(f"🚀 Kushagra Engine LIVE on Port: {PORT}")
    httpd.serve_forever()

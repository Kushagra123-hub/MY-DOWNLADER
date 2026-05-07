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
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (id INTEGER PRIMARY KEY, username TEXT, api_key TEXT UNIQUE)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Setup Error: {e}")

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

        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            try:
                with open("index.html", "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f.read())
            except:
                self.send_json({"error": "UI not found"}, 404)
            return

        elif parsed_path.path == "/api/register":
            name = query.get("name", [None])[0]
            if not name:
                self.send_json({"error": "Name needed"}, 400)
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
                self.send_json({"error": "Registration failed"}, 500)

        elif parsed_path.path == "/api/engine":
            key = query.get("key", [None])[0]
            video_url = query.get("url", [None])[0]

            # API Key Check
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT username FROM users WHERE api_key=?", (key,))
            user = c.fetchone()
            conn.close()

            if not user:
                self.send_json({"error": "Invalid Key"}, 401)
                return

            try:
                # पक्का करो कि cookies.txt है या नहीं
                cookie_path = 'cookies.txt'
                
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    # अगर फाइल है तभी इस्तेमाल करो, वरना छोड़ दो
                    'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios'],
                        }
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                
                self.send_json({
                    "status": "success",
                    "title": info.get('title'),
                    "download_url": info.get('url')
                })
            except Exception as e:
                # यहाँ हम असली एरर भेजेंगे ताकि पता चले कि क्या गड़बड़ है
                self.send_json({"error": str(e)}, 500)

        else:
            super().do_GET()

PORT = int(os.environ.get("PORT", 8000))
# "0.0.0.0" रेंडर के लिए बहुत ज़रूरी है
with socketserver.TCPServer(("0.0.0.0", PORT), KushagraEngineHandler) as httpd:
    print(f"🚀 Kushagra Engine LIVE on Port: {PORT}")
    httpd.serve_forever()

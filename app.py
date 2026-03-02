from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import sqlite3
import os
import re

app = Flask(__name__)

# ÖNEMLİ: Veritabanını /tmp/ klasörüne kuruyoruz.
# Render'da /tmp/ klasörü her zaman yazılabilir alandır.
DB_PATH = "/tmp/iptv.db"

def init_db():
    """Veritabanı tablosunu oluştur"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channels 
                 (id TEXT PRIMARY KEY, name TEXT, url TEXT)''')
    conn.commit()
    conn.close()

# Uygulama başlarken veritabanını hazırla
init_db()

def get_all_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, url FROM channels")
    data = c.fetchall()
    conn.close()
    # Sözlük formatına çevir
    return {row[0]: {'name': row[1], 'url': row[2]} for row in data}

def add_channel_db(safe_id, name, url):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO channels (id, name, url) VALUES (?, ?, ?)", 
                  (safe_id, name, url))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Hatası: {e}")
        return False

def delete_channel_db(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id=?", (channel_id,))
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def panel():
    message = ""
    
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                if add_channel_db(safe_id, name, url):
                    message = f"✅ EKLENDİ: {name}"
                else:
                    message = "❌ Veritabanı Hatası!"
            else:
                message = "❌ İsim veya URL geçersiz"
                
        elif 'delete' in request.form:
            id_del = request.form.get('delete')
            delete_channel_db(id_del)
            message = "🗑️ Silindi"

    # Kanalları veritabanından çek
    channels = get_all_channels()

    html = """
    <!DOCTYPE html>
    <body style="background:#111; color:#fff; font-family:monospace; padding:20px;">
        <div style="max-width:600px; margin:auto;">
            <h2>💾 Veritabanlı Panel (/tmp)</h2>
            
            {% if message %}
            <div style="padding:10px; background:#333; color:yellow; border:1px solid yellow; margin-bottom:10px;">
                {{ message }}
            </div>
            {% endif %}

            <div style="background:#222; padding:15px; border-radius:5px;">
                <form method="POST">
                    <input type="text" name="name" placeholder="Kanal Adı (Örn: Fox)" required style="width:100%; padding:10px; margin-bottom:5px;">
                    <input type="text" name="url" placeholder="YouTube Linki" required style="width:100%; padding:10px; margin-bottom:5px;">
                    <button style="width:100%; padding:10px; background:blue; color:white; border:none; cursor:pointer;">KAYDET</button>
                </form>
            </div>

            <hr style="border-color:#444; margin:20px 0;">

            <h3>Kanal Listesi ({{ channels|length }})</h3>
            
            {% if channels|length == 0 %}
                <div style="color:red; text-align:center;">LİSTE BOŞ - Lütfen kanal ekleyin.</div>
            {% else %}
                {% for id, data in channels.items() %}
                <div style="background:#1a1a1a; padding:10px; margin-bottom:10px; border-left:4px solid #00e676;">
                    <strong style="font-size:18px;">{{ data.name }}</strong>
                    <div style="margin-top:5px;">
                        <a href="/stream/{{ id }}" target="_blank" style="color:#00e676; font-size:12px;">{{ request.host_url }}stream/{{ id }}</a>
                    </div>
                    <form method="POST" style="margin-top:5px;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button style="background:#d32f2f; color:white; border:none; padding:5px 10px; cursor:pointer;">SİL</button>
                    </form>
                </div>
                {% endfor %}
            {% endif %}
            
            <p style="font-size:11px; color:#666;">Veritabanı Konumu: /tmp/iptv.db</p>
        </div>
    </body>
    """
    return render_template_string(html, channels=channels, message=message)

@app.route('/stream/<channel_id>')
def stream_video(channel_id):
    channels = get_all_channels()
    if channel_id not in channels:
        return "Kanal Bulunamadı", 404
    
    target_url = channels[channel_id]['url']

    # yt-dlp komutu
    cmd = [
        "yt-dlp", 
        "-f", "best",
        "-o", "-",
        "--force-ipv4",
        "--no-warnings",
        target_url
    ]
    
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate():
        first_chunk = process.stdout.read(1024)
        if not first_chunk:
            error = process.stderr.read().decode('utf-8', errors='ignore')
            yield f"Yayın Hatası: {error}".encode()
            return
        yield first_chunk
        try:
            while True:
                data = process.stdout.read(16384)
                if not data: break
                yield data
        except: pass
        finally:
            if process.poll() is None: process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp4')

if __name__ == '__main__':
    # Veritabanını başlat
    init_db()
    app.run(host='0.0.0.0', port=10000)

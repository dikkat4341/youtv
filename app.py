from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import json
import os
import re

app = Flask(__name__)

DATA_FILE = "channels.json"

# --- YARDIMCI FONKSİYONLAR ---
def load_channels():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_channels(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- PANEL ARAYÜZÜ ---
@app.route('/', methods=['GET', 'POST'])
def panel():
    channels = load_channels()
    
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                channels[safe_id] = {'url': url, 'name': name}
                save_channels(channels)
                
        elif 'delete' in request.form:
            id_del = request.form.get('delete')
            if id_del in channels:
                del channels[id_del]
                save_channels(channels)
        return redirect('/')

    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Pro Stream Panel v2</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: monospace; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            input, button { background: #333; border: 1px solid #444; color: white; padding: 10px; width: 100%; margin-bottom: 10px; }
            button { background: #007bff; cursor: pointer; }
            .item { background: #1e1e1e; padding: 15px; margin-bottom: 10px; border-left: 5px solid #00e676; }
            .url { color: #00e676; word-break: break-all; font-size: 12px; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔴 YouTube Proxy Streamer V2</h2>
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı (Örn: KralFM)" required>
                <input type="text" name="url" placeholder="YouTube Linki" required>
                <button type="submit" name="add">KANAL EKLE</button>
            </form>
            <hr>
            {% for id, data in channels.items() %}
            <div class="item">
                <strong>{{ data.name }}</strong>
                <div class="url">{{ request.host_url }}stream/{{ id }}</div>
                <form method="POST" style="margin-top:5px;">
                    <input type="hidden" name="delete" value="{{ id }}">
                    <button type="submit" style="background:#b71c1c;">SİL</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=channels)

# --- PROXY STREAM API ---
@app.route('/stream/<channel_id>')
def stream_proxy(channel_id):
    channels = load_channels()
    if channel_id not in channels:
        return "Kanal bulunamadı", 404

    youtube_url = channels[channel_id]['url']
    
    # 1. Komutu hazırla: yt-dlp direkt yayını standart çıktıya (stdout) basacak
    # -f best: En iyi kaliteyi bul
    # -o - : Dosyaya değil ekrana bas (pipe)
    cmd = [
        "yt-dlp",
        "-f", "best",
        "-o", "-", 
        youtube_url
    ]
    
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    # 2. İşlemi Başlat
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE  # Hataları yakalamak için
        )
    except Exception as e:
        return f"Sistem hatası: {str(e)}", 500

    # 3. Yayını parça parça kullanıcıya gönder (Generator)
    def generate():
        try:
            while True:
                # 8KB veri oku
                data = process.stdout.read(8192)
                if not data:
                    # Veri bittiyse hata var mı kontrol et
                    stderr_output = process.stderr.read().decode('utf-8')
                    if stderr_output:
                        print("Yayın Hatası:", stderr_output) # Loglara yaz
                    break
                yield data
        except Exception as e:
            process.kill()
        finally:
            if process.poll() is None:
                process.kill()

    # Eğer işlem hemen öldüyse hata mesajını döndür
    if process.poll() is not None:
         return f"Yayın başlatılamadı. YouTube linkini kontrol et.", 500

    return Response(stream_with_context(generate()), mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

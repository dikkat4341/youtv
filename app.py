from flask import Flask, request, render_template_string, Response, stream_with_context
import subprocess
import os
import re
import json

app = Flask(__name__)

# Başlangıçta TRT Haber (Test için)
CHANNELS = {
    "trt": {
        "name": "damarr",
        "url": "https://www.youtube.com/watch?v=N1VogsSbe6M"
    }
}

@app.route('/', methods=['GET', 'POST'])
def panel():
    global CHANNELS
    msg = ""

    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                CHANNELS[safe_id] = {'name': name, 'url': url}
                msg = f"✅ {name} eklendi!"
            else:
                msg = "❌ Eksik bilgi."

        elif 'delete' in request.form:
            del_id = request.form.get('delete')
            if del_id in CHANNELS:
                del CHANNELS[del_id]
                msg = "🗑️ Silindi."

    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Zırhlı Panel</title>
        <style>
            body { background: #111; color: #fff; font-family: monospace; padding: 20px; }
            .container { max-width: 600px; margin: auto; border: 1px solid #333; padding: 20px; }
            input, button { width: 100%; padding: 10px; margin: 5px 0; border: none; }
            button { cursor: pointer; background: blue; color: white; }
            .item { background: #222; padding: 10px; margin-bottom: 5px; border-left: 3px solid #0f0; }
            a { color: #0f0; word-break: break-all; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🛡️ Zırhlı Panel (Cache Fix)</h2>
            {% if msg %}<div style="background:#333; padding:10px; margin-bottom:10px;">{{ msg }}</div>{% endif %}
            
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required>
                <input type="text" name="url" placeholder="YouTube Linki" required>
                <button name="add">EKLE</button>
            </form>
            <hr>
            {% for id, data in channels.items() %}
            <div class="item">
                <strong>{{ data.name }}</strong><br>
                <a href="/stream/{{ id }}" target="_blank">{{ request.host_url }}stream/{{ id }}</a>
                <form method="POST" style="margin-top:5px;">
                    <input type="hidden" name="delete" value="{{ id }}">
                    <button style="background:red; width:auto; padding:5px;">SİL</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=CHANNELS, msg=msg)

@app.route('/stream/<cid>')
def stream_video(cid):
    if cid not in CHANNELS:
        return "Kanal Bulunamadı", 404
    
    target_url = CHANNELS[cid]['url']

    # 1. ADIM: YouTube Linkini Al (Hata Ayıklamalı)
    # Render'da /tmp/ klasörünü cache için kullanıyoruz.
    cmd_get = [
        "yt-dlp", 
        "-g", 
        "-f", "best",
        "--cache-dir", "/tmp/",       # KRİTİK: Render'da yazılabilir tek yer burası
        "--no-warnings",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        target_url
    ]

    # Cookies varsa ekle
    if os.path.exists("cookies.txt"):
        cmd_get.extend(["--cookies", "cookies.txt"])

    # Komutu çalıştır ve hatayı yakala
    try:
        result = subprocess.run(cmd_get, capture_output=True, text=True)
        
        # Eğer hata varsa, stderr çıktısını göster
        if result.returncode != 0:
            return f"<h1>YT-DLP HATASI:</h1><pre>{result.stderr}</pre>", 500
            
        real_url = result.stdout.strip()
        
    except Exception as e:
        return f"Sistem Hatası: {str(e)}", 500

    # 2. ADIM: FFMPEG ile Yayını İlet
    ffmpeg_cmd = [
        "ffmpeg",
        "-re",
        "-i", real_url,
        "-c", "copy",
        "-f", "mpegts",
        "-movflags", "frag_keyframe+empty_moov",
        "pipe:1"
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate():
        # İlk veriyi oku (Hata kontrolü)
        chunk = process.stdout.read(1024)
        if not chunk:
            err = process.stderr.read().decode()
            yield f"FFMPEG Hatası: {err}".encode()
            return
        
        yield chunk
        try:
            while True:
                data = process.stdout.read(32768)
                if not data: break
                yield data
        except:
            pass
        finally:
            if process.poll() is None: process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp2t')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

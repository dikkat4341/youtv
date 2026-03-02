from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import json
import os
import re
import time

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

def get_real_youtube_url(youtube_url):
    """yt-dlp kullanarak gerçek HLS linkini alır"""
    cmd = [
        "yt-dlp", 
        "-g", 
        "-f", "best", # En iyi kaliteyi seç
        youtube_url
    ]
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])
        
    try:
        # Linki al ve temizle
        direct_url = subprocess.check_output(cmd).decode('utf-8').strip()
        return direct_url
    except Exception as e:
        print(f"Hata: {e}")
        return None

# --- PANEL ARAYÜZÜ ---
@app.route('/', methods=['GET', 'POST'])
def panel():
    channels = load_channels()
    
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            # ID temizleme
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
        <title>Pro Stream Panel</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: monospace; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            input, button { background: #333; border: 1px solid #444; color: white; padding: 10px; width: 100%; margin-bottom: 10px; }
            button { background: #007bff; cursor: pointer; }
            .item { background: #1e1e1e; padding: 15px; margin-bottom: 10px; border-left: 5px solid #007bff; }
            .url { color: #00ff00; word-break: break-all; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔴 YouTube Proxy Streamer</h2>
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı (Örn: CNN)" required>
                <input type="text" name="url" placeholder="YouTube Linki" required>
                <button type="submit" name="add">KANAL EKLE</button>
            </form>
            <hr>
            {% for id, data in channels.items() %}
            <div class="item">
                <h3>{{ data.name }}</h3>
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

# --- PROXY STREAM API (PROFESYONEL KISIM) ---
@app.route('/stream/<channel_id>')
def stream_proxy(channel_id):
    channels = load_channels()
    if channel_id not in channels:
        return "Kanal bulunamadı", 404

    youtube_url = channels[channel_id]['url']
    
    # 1. Gerçek yayın linkini al (yt-dlp)
    real_url = get_real_youtube_url(youtube_url)
    if not real_url:
        return "Yayın linki alınamadı", 500

    # 2. FFMPEG ile yayını sunucuya çek ve anlık olarak kullanıcıya bas
    # Bu işlem CPU kullanır ama IP kilidini kesin çözer.
    ffmpeg_cmd = [
        'ffmpeg',
        '-re',
        '-i', real_url,       # Giriş: YouTube HLS linki
        '-c', 'copy',         # Kodlama yapma (CPU dostu, direkt kopyala)
        '-f', 'mpegts',       # Çıkış formatı: MPEG-TS (IPTV için standart)
        '-movflags', 'frag_keyframe+empty_moov',
        'pipe:1'              # Çıktıyı doğrudan Python'a ver
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def generate():
        try:
            while True:
                # 4KB'lık parçalar halinde oku ve gönder
                data = process.stdout.read(4096)
                if not data:
                    break
                yield data
        finally:
            # Kullanıcı çıkarsa işlemi öldür
            process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp2t')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

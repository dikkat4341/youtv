from flask import Flask, request, redirect, render_template_string, jsonify
import subprocess
import json
import os
import re

app = Flask(__name__)

DATA_FILE = "channels.json"

# Veri dosyasını kontrol et ve yükle
def load_channels():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_channels(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# YouTube ID ayıklama
def get_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

# --- PANEL KISMI (HTML ARAYÜZ) ---
@app.route('/', methods=['GET', 'POST'])
def panel():
    channels = load_channels()
    
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name') # Kanal Adı (ID olarak kullanılacak)
            url = request.form.get('url')
            
            # Boşlukları temizle ve güvenli ID yap
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                channels[safe_id] = {'url': url, 'name': name}
                save_channels(channels)
                
        elif 'delete' in request.form:
            channel_id = request.form.get('delete')
            if channel_id in channels:
                del channels[channel_id]
                save_channels(channels)
        
        return redirect('/')

    # HTML Şablonu (PHP gibi)
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YT Live Streamer</title>
        <style>
            body { font-family: sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            input, button { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; }
            .item { background: #333; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
            .link { color: #4CAF50; word-break: break-all; }
            button { cursor: pointer; background: #2196F3; color: white; border: none; }
            .del-btn { background: #f44336; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📺 YouTube to M3U8 Panel</h2>
            
            <form method="POST" style="background:#222; padding:20px; border-radius:8px;">
                <input type="text" name="name" placeholder="Kanal Adı (Örn: showtv)" required>
                <input type="text" name="url" placeholder="YouTube Canlı Yayın Linki" required>
                <button type="submit" name="add">Kanal Ekle</button>
            </form>

            <hr>

            <h3>Kayıtlı Kanallar</h3>
            {% for id, data in channels.items() %}
            <div class="item">
                <strong>{{ data.name }}</strong><br>
                <small>Orijinal: {{ data.url }}</small><br><br>
                
                Canlı Yayın Linkin (M3U8):<br>
                <div class="link">
                    {{ request.host_url }}live/{{ id }}.m3u8
                </div>
                
                <form method="POST">
                    <input type="hidden" name="delete" value="{{ id }}">
                    <button type="submit" class="del-btn">Sil</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=channels)

# --- STREAM API (M3U8 ÜRETİCİ) ---
@app.route('/live/<channel_id>.m3u8')
def stream_redirect(channel_id):
    channels = load_channels()
    
    if channel_id not in channels:
        return "Kanal bulunamadi", 404

    target_url = channels[channel_id]['url']
    
    # yt-dlp komutu: Canlı yayın linkini al (cookies.txt varsa kullanır)
    cmd = [
        "yt-dlp", 
        "-g", 
        target_url
    ]
    
    # Eğer cookies.txt varsa komuta ekle
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    try:
        # Linki al
        direct_url = subprocess.check_output(cmd).decode('utf-8').strip()
        
        # Oynatıcıyı gerçek linke yönlendir (302 Redirect)
        # Bu sayede sunucun yorulmaz, trafiği Google sunucuları taşır.
        return redirect(direct_url, code=302)
        
    except Exception as e:
        return f"Hata oluştu: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

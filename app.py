from flask import Flask, request, redirect, render_template_string
import subprocess
import json
import os
import re

app = Flask(__name__)

DATA_FILE = "channels.json"

# Veri yükleme/kaydetme
def load_channels():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_channels(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Panel Arayüzü
@app.route('/', methods=['GET', 'POST'])
def panel():
    channels = load_channels()
    
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            # ID temizleme (sadece harf rakam)
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

    # HTML Tasarımı
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IPTV Panel</title>
        <style>
            body { font-family: sans-serif; background: #0f0f0f; color: #fff; padding: 20px; }
            .box { background: #1f1f1f; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
            input, button { width: 100%; padding: 12px; margin: 5px 0; box-sizing: border-box; border-radius: 4px; border:none;}
            input { background: #333; color: white; }
            button { background: #e50914; color: white; cursor: pointer; font-weight: bold; }
            .list-item { border-bottom: 1px solid #333; padding: 15px 0; }
            .m3u-link { color: #00e676; font-family: monospace; word-break: break-all; background: #000; padding: 10px; border-radius: 4px; display: block; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div style="max-width: 600px; margin: auto;">
            <h2>📺 Stream Yöneticisi</h2>
            
            <div class="box">
                <form method="POST">
                    <input type="text" name="name" placeholder="Kanal Adı (Örn: ShowTV)" required>
                    <input type="text" name="url" placeholder="YouTube Canlı Linki" required>
                    <button type="submit" name="add">EKLE</button>
                </form>
            </div>

            <div class="box">
                <h3>Kanal Listesi</h3>
                {% for id, data in channels.items() %}
                <div class="list-item">
                    <strong>{{ data.name }}</strong>
                    <div class="m3u-link">
                        {{ request.host_url }}live/{{ id }}.m3u8
                    </div>
                    <form method="POST" style="margin-top:5px;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button type="submit" style="background:#444; width:auto; padding:5px 15px;">SİL</button>
                    </form>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=channels)

# M3U8 Link Üretici
@app.route('/live/<channel_id>.m3u8')
def stream(channel_id):
    channels = load_channels()
    if channel_id not in channels:
        return "Kanal Yok", 404

    target = channels[channel_id]['url']
    
    # yt-dlp komutu
    cmd = ["yt-dlp", "-g", target]
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    try:
        # Linki al
        direct_url = subprocess.check_output(cmd).decode('utf-8').strip()
        # Kullanıcıyı yönlendir
        return redirect(direct_url, code=302)
    except:
        return "Yayin alinamadi", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

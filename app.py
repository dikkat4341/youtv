from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import json
import os
import re
import sys

app = Flask(__name__)

# Dosya yolunu tam belirtelim (Hata şansını sıfıra indirir)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "channels.json")

def load_channels():
    # Dosya yoksa oluştur
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_channels(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("Kayıt başarılı:", data) # Loglara yaz
        return True
    except Exception as e:
        print("Kayıt hatası:", e)
        return False

@app.route('/', methods=['GET', 'POST'])
def panel():
    channels = load_channels()
    message = ""

    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            
            # ID oluştur (Boşlukları sil, küçük harf yap)
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                channels[safe_id] = {'url': url, 'name': name}
                if save_channels(channels):
                    message = f"✅ {name} eklendi!"
                else:
                    message = "❌ Dosya yazma hatası!"
            else:
                message = "❌ İsim veya URL geçersiz."
                
        elif 'delete' in request.form:
            id_to_del = request.form.get('delete')
            if id_to_del in channels:
                del channels[id_to_del]
                save_channels(channels)
                message = "🗑️ Kanal silindi."
        
        # Sayfayı yenilemeden veriyi güncellemek için kanalları tekrar yükle
        channels = load_channels()

    # HTML ARAYÜZÜ
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Stream Panel Final</title>
        <style>
            body { background: #111; color: #eee; font-family: sans-serif; padding: 20px; }
            .container { max-width: 700px; margin: 0 auto; background: #222; padding: 20px; border-radius: 8px; }
            input, button { width: 100%; padding: 12px; margin: 5px 0; border: none; border-radius: 4px; box-sizing: border-box; }
            input { background: #333; color: white; border: 1px solid #444; }
            button.add { background: #28a745; color: white; font-weight: bold; cursor: pointer; }
            button.del { background: #dc3545; color: white; width: auto; padding: 5px 15px; cursor: pointer; float: right; }
            .item { background: #1a1a1a; padding: 15px; margin-bottom: 10px; border-left: 5px solid #007bff; clear: both; overflow: auto; }
            .link { color: #00e676; font-family: monospace; font-size: 12px; margin-top: 5px; display: block; }
            .msg { padding: 10px; margin-bottom: 10px; border-radius: 4px; text-align: center; }
            .success { background: #155724; color: #d4edda; }
            .error { background: #721c24; color: #f8d7da; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="text-align:center">📺 Stream Yöneticisi</h2>
            
            {% if message %}
                <div class="msg {% if '❌' in message %}error{% else %}success{% endif %}">
                    {{ message }}
                </div>
            {% endif %}

            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı (Örn: ShowTV)" required>
                <input type="text" name="url" placeholder="YouTube Linki" required>
                <button type="submit" class="add" name="add">KANAL EKLE</button>
            </form>

            <hr style="border-color:#444; margin: 20px 0;">

            <h3>Kanal Listesi ({{ channels|length }})</h3>

            {% if channels|length == 0 %}
                <p style="text-align:center; color:#777;">Henüz hiç kanal eklenmedi.</p>
            {% else %}
                {% for id, data in channels.items() %}
                <div class="item">
                    <strong style="font-size:18px;">{{ data.name }}</strong>
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button type="submit" class="del">SİL</button>
                    </form>
                    
                    <span class="link">
                        {{ request.host_url }}stream/{{ id }}
                    </span>
                </div>
                {% endfor %}
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=channels, message=message)

# --- STREAM API ---
@app.route('/stream/<channel_id>')
def stream_video(channel_id):
    channels = load_channels()
    if channel_id not in channels:
        return "Kanal Bulunamadı! Listeyi kontrol edin.", 404
    
    target_url = channels[channel_id]['url']

    # Streamlink komutu
    # --hls-segment-threads 2: Yayını hızlandırır
    # best: En iyi kalite
    cmd = ["streamlink", "--stdout", target_url, "best", "--hls-segment-threads", "2"]
    
    if os.path.exists(os.path.join(BASE_DIR, "cookies.txt")):
        cmd.extend(["--http-cookies", os.path.join(BASE_DIR, "cookies.txt")])

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return f"Stream Başlatılamadı: {str(e)}", 500

    def generate():
        try:
            # Hata kontrolü için ilk datayı bekle
            first_byte = process.stdout.read(1)
            if not first_byte:
                error = process.stderr.read().decode('utf-8', errors='ignore')
                yield f"Yayın Hatası (Log): {error}".encode()
                return
            yield first_byte

            while True:
                data = process.stdout.read(32768) # 32KB Buffer
                if not data:
                    break
                yield data
        except:
            pass
        finally:
            if process.poll() is None:
                process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

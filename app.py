from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import json
import os
import re

app = Flask(__name__)

DATA_FILE = "channels.json"

def load_channels():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_channels(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
            del channels[request.form.get('delete')]
            save_channels(channels)
        return redirect('/')

    html = """
    <!DOCTYPE html>
    <body style="background:#111; color:#fff; font-family:sans-serif; padding:20px;">
        <div style="max-width:600px; margin:auto;">
            <h2>🚀 Streamlink Panel</h2>
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required style="width:100%; padding:10px; margin:5px 0;">
                <input type="text" name="url" placeholder="YouTube Linki" required style="width:100%; padding:10px; margin:5px 0;">
                <button style="width:100%; padding:10px; background:blue; color:white; border:none;">EKLE</button>
            </form>
            <hr>
            {% for id, data in channels.items() %}
            <div style="background:#222; padding:10px; margin-bottom:10px; border-left:4px solid lime;">
                <strong>{{ data.name }}</strong>
                <div style="color:lime; font-size:12px; margin-top:5px; word-break:break-all;">
                    {{ request.host_url }}stream/{{ id }}
                </div>
                <form method="POST" style="margin-top:5px;">
                    <input type="hidden" name="delete" value="{{ id }}">
                    <button style="background:red; color:white; border:none; padding:5px;">SİL</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </body>
    """
    return render_template_string(html, channels=channels)

# --- STREAMLINK API ---
@app.route('/stream/<channel_id>')
def stream_video(channel_id):
    channels = load_channels()
    if channel_id not in channels:
        return "Kanal Yok", 404
    
    target_url = channels[channel_id]['url']

    # Komut: streamlink --stdout "URL" best
    # Bu komut veriyi direkt olarak Python'a akıtır.
    cmd = ["streamlink", "--stdout", target_url, "best"]
    
    # Cookies varsa ekle (Çok Önemli!)
    if os.path.exists("cookies.txt"):
        cmd.extend(["--http-cookies", "cookies.txt"]) # Streamlink için parametre farklı olabilir ama genelde otomatik algılar veya --http-cookie gerektirir.
        # Basitlik için streamlink genelde cookies dosyasını -c ile almaz, 
        # ama bu örnekte parametre karmaşası olmasın diye sade bırakıyoruz.
        # Eğer cookies gerekirse environment variable olarak eklemek daha iyidir.

    try:
        # İşlemi başlat
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return f"Başlatma Hatası: {str(e)}", 500

    # Veri akış fonksiyonu
    def generate():
        try:
            # Hata kontrolü için ilk başta biraz bekle
            # Eğer streamlink hemen ölürse hata mesajını yakalayalım
            output = process.stdout.read(1024) 
            if not output:
                error_msg = process.stderr.read().decode('utf-8')
                yield f"Streamlink Hatası: {error_msg}".encode()
                return

            yield output
            
            # Sonsuz döngüde veriyi akıt
            while True:
                data = process.stdout.read(16384) # 16KB parçalar
                if not data:
                    break
                yield data
        except Exception:
            pass
        finally:
            process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp4') # MPEG-TS akışı

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

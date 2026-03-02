from flask import Flask, request, redirect, render_template_string, Response, stream_with_context
import subprocess
import re
import os
import time

app = Flask(__name__)

# Verileri RAM'de tut
CHANNELS = {}

@app.route('/', methods=['GET', 'POST'])
def panel():
    global CHANNELS
    message = ""
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            if safe_id and url:
                CHANNELS[safe_id] = {'url': url, 'name': name}
                message = f"✅ Eklendi: {name}"
        elif 'delete' in request.form:
            id_del = request.form.get('delete')
            if id_del in CHANNELS:
                del CHANNELS[id_del]
                message = "🗑️ Silindi"

    html = """
    <!DOCTYPE html>
    <body style="background:#111; color:#fff; font-family:monospace; padding:20px;">
        <div style="max-width:600px; margin:auto;">
            <h2>🛠️ Debug Stream Panel</h2>
            {% if message %}<div style="border:1px solid lime; color:lime; padding:10px; margin-bottom:10px;">{{ message }}</div>{% endif %}
            
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required style="width:100%; padding:10px; margin-bottom:5px;">
                <input type="text" name="url" placeholder="YouTube Linki" required style="width:100%; padding:10px; margin-bottom:5px;">
                <button style="width:100%; padding:10px; background:blue; color:white; border:none;">EKLE</button>
            </form>
            <hr>
            <h3>Kayıtlı Kanallar:</h3>
            {% for id, data in channels.items() %}
            <div style="background:#222; padding:10px; margin-bottom:10px;">
                <strong>{{ data.name }}</strong><br>
                <a href="/stream/{{ id }}" target="_blank" style="color:yellow; word-break:break-all;">{{ request.host_url }}stream/{{ id }}</a>
                <form method="POST" style="margin-top:5px;"><input type="hidden" name="delete" value="{{ id }}"><button style="background:red; color:white; border:none; padding:5px;">SİL</button></form>
            </div>
            {% endfor %}
            <p style="color:#777; font-size:12px;">Not: Linke tıkladığınızda yayın açılmazsa ekranda hata kodu yazar.</p>
        </div>
    </body>
    """
    return render_template_string(html, channels=CHANNELS, message=message)

@app.route('/stream/<channel_id>')
def stream_video(channel_id):
    if channel_id not in CHANNELS:
        return "Kanal Bulunamadı", 404
    
    target_url = CHANNELS[channel_id]['url']

    # yt-dlp komutu:
    # -f best: En iyi kalite
    # --force-ipv4: Render'ın IPv6 sorununu çözer
    cmd = [
        "yt-dlp", 
        "-f", "best",
        "-o", "-",             # Çıktıyı ekrana bas (Pipe)
        "--force-ipv4",        # IP sorununu çözmeye çalış
        "--no-warnings",
        target_url
    ]
    
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate():
        # İlk veriyi okumayı dene
        # Eğer hemen hata verirse, stderr (hata) çıktısını kullanıcıya göster
        first_chunk = process.stdout.read(1024)
        
        if not first_chunk:
            # Yayın gelmedi, hatayı oku
            error_message = process.stderr.read().decode('utf-8', errors='ignore')
            yield f"⚠️ YAYIN HATASI OLUŞTU:\n\n{error_message}\n\nÇÖZÜM: 'cookies.txt' yüklemeniz veya URL'yi kontrol etmeniz gerekiyor.".encode()
            return

        yield first_chunk
        
        # Yayın akmaya başladıysa devam et
        try:
            while True:
                data = process.stdout.read(4096)
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

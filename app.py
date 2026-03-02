from flask import Flask, request, render_template_string, Response, stream_with_context
import subprocess
import os
import re

app = Flask(__name__)

# Verileri Hafızada Tut (RAM)
# Tek işlemci olduğu için artık silinmez.
CHANNELS = {}

@app.route('/', methods=['GET', 'POST'])
def panel():
    global CHANNELS
    msg = ""

    if request.method == 'POST':
        # EKLEME İŞLEMİ
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            # ID oluştur
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                CHANNELS[safe_id] = {'name': name, 'url': url}
                msg = f"✅ {name} Eklendi!"
            else:
                msg = "❌ Hata: İsim veya URL eksik."

        # SİLME İŞLEMİ
        elif 'delete' in request.form:
            del_id = request.form.get('delete')
            if del_id in CHANNELS:
                del CHANNELS[del_id]
                msg = "🗑️ Silindi."

    # HTML ARAYÜZÜ
    html = """
    <!DOCTYPE html>
    <body style="background:#111; color:#fff; font-family:sans-serif; padding:20px;">
        <div style="max-width:600px; margin:auto; border:1px solid #333; padding:20px;">
            <h2 style="color:#0f0;">⚡ Basit Panel</h2>
            
            {% if msg %}
            <div style="background:#222; padding:10px; margin-bottom:10px; border:1px solid #555;">{{ msg }}</div>
            {% endif %}

            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required style="width:100%; padding:10px; margin-bottom:5px;">
                <input type="text" name="url" placeholder="YouTube Linki" required style="width:100%; padding:10px; margin-bottom:5px;">
                <button name="add" style="width:100%; padding:10px; background:blue; color:white; border:none; cursor:pointer;">EKLE</button>
            </form>

            <hr style="border-color:#333; margin:20px 0;">

            <h3>LİSTE ({{ channels|length }})</h3>
            
            {% if channels|length == 0 %}
                <p style="color:red;">Liste Boş.</p>
            {% else %}
                {% for id, data in channels.items() %}
                <div style="background:#222; padding:10px; margin-bottom:5px; border-left:3px solid #0f0;">
                    <strong>{{ data.name }}</strong>
                    <br>
                    <a href="/stream/{{ id }}" target="_blank" style="color:#0f0; font-size:12px;">{{ request.host_url }}stream/{{ id }}</a>
                    <form method="POST" style="margin-top:5px;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button style="background:#d00; color:#fff; border:none; padding:5px; cursor:pointer;">SİL</button>
                    </form>
                </div>
                {% endfor %}
            {% endif %}
        </div>
    </body>
    """
    return render_template_string(html, channels=CHANNELS, msg=msg)

@app.route('/stream/<cid>')
def stream(cid):
    if cid not in CHANNELS:
        return "Kanal Yok", 404
    
    url = CHANNELS[cid]['url']
    
    # Yayın Komutu
    cmd = ["yt-dlp", "-f", "best", "-o", "-", "--force-ipv4", url]
    
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    # Yayını başlat
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate():
        # İlk veriyi oku (Hata varsa ekrana basmak için)
        first = process.stdout.read(1024)
        if not first:
            err = process.stderr.read().decode()
            yield f"Yayın Hatası: {err}".encode()
            return
        
        yield first
        # Devamını akıt
        try:
            while True:
                data = process.stdout.read(16384)
                if not data: break
                yield data
        except:
            pass
        finally:
            if process.poll() is None: process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp4')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

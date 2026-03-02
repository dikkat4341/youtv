from flask import Flask, request, render_template_string, Response, stream_with_context
import subprocess
import os
import re
import time

app = Flask(__name__)

# --- HAFIZA (RAM) ---
# TRT Haber'i varsayılan olarak ekledim.
# Sistem açıldığında direkt bunu dene. Eklemeyle uğraşma.
CHANNELS = {
    "trt": {
        "name": "DAMAR FM",
        "url": "https://www.youtube.com/watch?v=N1VogsSbe6M" 
    }
}

@app.route('/', methods=['GET', 'POST'])
def panel():
    global CHANNELS
    msg = ""

    # KANAL EKLEME / SİLME İŞLEMLERİ
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            # Türkçe karakterleri ve boşlukları temizleyip ID yap
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                CHANNELS[safe_id] = {'name': name, 'url': url}
                msg = f"✅ {name} eklendi! Listeye bak."
            else:
                msg = "❌ Hata: İsim veya URL eksik."

        elif 'delete' in request.form:
            del_id = request.form.get('delete')
            if del_id in CHANNELS:
                del CHANNELS[del_id]
                msg = "🗑️ Silindi."

    # HTML ARAYÜZÜ
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Kesin Çözüm Panel</title>
        <style>
            body { background: #0d0d0d; color: #fff; font-family: sans-serif; padding: 20px; }
            .container { max-width: 600px; margin: auto; border: 1px solid #333; padding: 20px; border-radius: 10px; }
            input, button { width: 100%; padding: 12px; margin: 5px 0; border-radius: 5px; border: none; box-sizing: border-box; }
            input { background: #222; color: white; border: 1px solid #444; }
            button.add { background: #007bff; color: white; font-weight: bold; cursor: pointer; }
            button.del { background: #dc3545; color: white; width: auto; padding: 5px 10px; cursor: pointer; float: right; }
            .item { background: #1a1a1a; padding: 15px; margin-bottom: 10px; border-left: 5px solid #28a745; overflow: hidden; }
            .link { color: #28a745; font-family: monospace; font-size: 13px; display: block; margin-top: 5px; word-break: break-all; }
            .msg { background: #333; color: yellow; padding: 10px; text-align: center; margin-bottom: 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="text-align:center">🚀 Final Stream Panel</h2>
            
            {% if msg %}
            <div class="msg">{{ msg }}</div>
            {% endif %}

            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı (Örn: ShowTV)" required>
                <input type="text" name="url" placeholder="YouTube Linki" required>
                <button class="add" name="add">KANAL EKLE</button>
            </form>

            <hr style="border-color:#333; margin: 25px 0;">

            <h3>Kanal Listesi ({{ channels|length }})</h3>
            
            {% for id, data in channels.items() %}
            <div class="item">
                <strong style="font-size:18px">{{ data.name }}</strong>
                <form method="POST" style="display:inline;">
                    <input type="hidden" name="delete" value="{{ id }}">
                    <button class="del">SİL</button>
                </form>
                <br>
                <span class="link">{{ request.host_url }}stream/{{ id }}</span>
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

    # --- ÖNEMLİ KISIM: FFMPEG RE-STREAM ---
    # 1. yt-dlp ile linki alıyoruz.
    # 2. ffmpeg ile indirip tarayıcıya "pipe" ediyoruz.
    # Bu yöntem IP kilidini %100 aşar çünkü YouTube sadece sunucuyu görür.
    
    # Gerçek video linkini al
    try:
        cmd_get_url = ["yt-dlp", "-g", "-f", "best", target_url]
        if os.path.exists("cookies.txt"):
            cmd_get_url.extend(["--cookies", "cookies.txt"])
            
        real_url = subprocess.check_output(cmd_get_url).decode().strip()
    except Exception as e:
        return f"Link alma hatası: {str(e)}", 500

    # FFMPEG Komutu (Kopyalama Modu - CPU dostu)
    ffmpeg_cmd = [
        "ffmpeg",
        "-re",
        "-i", real_url,        # Giriş: YouTube linki
        "-c", "copy",          # Video/Ses kodlaması yapma (Direkt kopyala)
        "-f", "mpegts",        # Format: IPTV standardı
        "-movflags", "frag_keyframe+empty_moov",
        "pipe:1"               # Çıktıyı Python'a ver
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate():
        try:
            while True:
                data = process.stdout.read(32768) # 32KB parça
                if not data:
                    break
                yield data
        except:
            pass
        finally:
            if process.poll() is None:
                process.kill()

    return Response(stream_with_context(generate()), mimetype='video/mp2t')

if __name__ == '__main__':
    # Tek işlemci, Threading açık
    app.run(host='0.0.0.0', port=10000, threaded=True)

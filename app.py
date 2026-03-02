from flask import Flask, request, render_template_string, Response, stream_with_context, redirect
import subprocess
import os
import re

app = Flask(__name__)

CHANNELS = {}

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

        elif 'delete' in request.form:
            del_id = request.form.get('delete')
            if del_id in CHANNELS:
                del CHANNELS[del_id]
                msg = "🗑️ Silindi"

    # Test kanalı ekle (boşsa)
    if not CHANNELS:
        CHANNELS["test"] = {"name": "Test Kanalı", "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk"}

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Final Panel</title>
        <style>
            body { background: #0a0a0a; color: #fff; font-family: system-ui; padding: 20px; }
            .box { max-width: 700px; margin: auto; background: #151515; padding: 25px; border-radius: 12px; }
            input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 6px; border: none; }
            input { background: #252525; color: #fff; }
            button.add { background: #00c853; color: #000; font-weight: bold; cursor: pointer; }
            button.del { background: #ff1744; color: #fff; width: auto; padding: 6px 12px; cursor: pointer; }
            .item { background: #1e1e1e; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #00c853; }
            .m3u8 { color: #00e676; font-family: monospace; font-size: 13px; word-break: break-all; }
            .mode { color: #aaa; font-size: 11px; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🚀 Final YouTube Panel</h2>
            {% if msg %}<div style="background: #1b5e20; padding: 12px; border-radius: 6px; margin-bottom: 15px;">{{ msg }}</div>{% endif %}
            
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required>
                <input type="text" name="url" placeholder="YouTube URL" required>
                <button class="add" name="add">KANAL EKLE</button>
            </form>
            
            <hr style="border-color: #333; margin: 20px 0;">
            
            <h3>Kanallar ({{ channels|length }})</h3>
            {% for id, data in channels.items() %}
            <div class="item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{{ data.name }}</strong>
                    <form method="POST" style="margin: 0;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button class="del">SİL</button>
                    </form>
                </div>
                
                <div class="m3u8">{{ request.host_url }}m3u8/{{ id }}</div>
                <div class="mode">Mod: Direkt → Proxy (Otomatik)</div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=CHANNELS, msg=msg)

@app.route('/m3u8/<cid>')
def get_m3u8(cid):
    """M3U8 playlist üret"""
    if cid not in CHANNELS:
        return "Kanal yok", 404
    
    base_url = request.host_url.rstrip('/')
    
    m3u8_content = f"""#EXTM3U
#EXTINF:-1,{CHANNELS[cid]['name']}
{base_url}/stream/{cid}
"""
    return Response(m3u8_content, mimetype='application/vnd.apple.mpegurl')

@app.route('/stream/<cid>')
def stream(cid):
    if cid not in CHANNELS:
        return "Kanal yok", 404
    
    yt_url = CHANNELS[cid]['url']
    
    # YÖNTEM 1: Direkt Link Al (Hızlı)
    try:
        cmd = [
            "yt-dlp",
            "-g",  # Sadece link ver
            "-f", "best[protocol^=m3u8]/best",  # HLS tercih et
            "--extractor-args", "youtube:player_client=web",
            "--no-check-certificates",
            "--geo-bypass",
            "--no-warnings",
            yt_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            direct_url = result.stdout.strip().split('\n')[0]  # İlk linki al
            
            # Yönlendirme dene (En hızlı yöntem)
            return redirect(direct_url, code=302)
            
    except Exception as e:
        pass  # Yöntem 1 başarısız, devam et
    
    # YÖNTEM 2: Proxy Stream (Ağır ama kesin)
    try:
        cmd = [
            "yt-dlp",
            "-f", "best",
            "-o", "-",
            "--extractor-args", "youtube:player_client=android",
            "--no-check-certificates",
            "--geo-bypass",
            yt_url
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        def generate():
            chunk = process.stdout.read(8192)
            if not chunk:
                err = process.stderr.read().decode()
                yield f"Stream hatası: {err[:500]}".encode()
                return
            
            yield chunk
            try:
                while True:
                    data = process.stdout.read(65536)  # 64KB buffer
                    if not data: break
                    yield data
            except:
                pass
            finally:
                if process.poll() is None:
                    process.kill()
        
        return Response(stream_with_context(generate()), mimetype='video/mp4')
        
    except Exception as e:
        return f"Proxy hatası: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

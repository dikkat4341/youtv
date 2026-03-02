from flask import Flask, request, render_template_string, Response, stream_with_context, redirect, jsonify
import subprocess
import os
import re

app = Flask(__name__)

CHANNELS = {}

@app.route('/', methods=['GET', 'POST'])
def panel():
    global CHANNELS
    msg = ""
    debug_info = ""

    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name')
            url = request.form.get('url')
            safe_id = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
            if safe_id and url:
                CHANNELS[safe_id] = {'name': name, 'url': url}
                msg = f"✅ {name} eklendi"

        elif 'delete' in request.form:
            del_id = request.form.get('delete')
            if del_id in CHANNELS:
                del CHANNELS[del_id]
                msg = "🗑️ Silindi"

    # Test modu
    test_result = None
    if request.args.get('test'):
        cid = request.args.get('test')
        if cid in CHANNELS:
            yt_url = CHANNELS[cid]['url']
            test_result = test_youtube_link(yt_url)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Panel</title>
        <style>
            body { background: #0a0a0a; color: #fff; font-family: monospace; padding: 20px; }
            .box { max-width: 800px; margin: auto; background: #151515; padding: 20px; border-radius: 8px; }
            input, button { padding: 10px; margin: 5px 0; border-radius: 4px; border: none; }
            input { background: #252525; color: #fff; width: 70%; }
            button { cursor: pointer; background: #00c853; color: #000; font-weight: bold; }
            button.test { background: #2196f3; color: #fff; }
            button.del { background: #ff1744; color: #fff; }
            .item { background: #1e1e1e; padding: 15px; margin: 10px 0; border-radius: 6px; }
            .debug { background: #000; color: #0f0; padding: 15px; margin: 15px 0; border-radius: 4px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; }
            .error { color: #ff5252; }
            .success { color: #69f0ae; }
            .links { margin: 10px 0; }
            .links a { color: #82b1ff; display: block; margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🔧 Debug Panel</h2>
            {% if msg %}<div style="background: #1b5e20; padding: 10px; margin-bottom: 15px; border-radius: 4px;">{{ msg }}</div>{% endif %}
            
            <form method="POST">
                <input type="text" name="name" placeholder="Kanal Adı" required>
                <input type="text" name="url" placeholder="YouTube URL" required style="width: 100%;">
                <button type="submit" name="add" style="width: 100%;">EKLE</button>
            </form>
            
            <hr style="border-color: #333; margin: 20px 0;">
            
            {% if test_result %}
            <h3>🧪 Test Sonucu</h3>
            <div class="debug">{{ test_result }}</div>
            <hr style="border-color: #333; margin: 20px 0;">
            {% endif %}
            
            <h3>Kanallar ({{ channels|length }})</h3>
            {% for id, data in channels.items() %}
            <div class="item">
                <strong>{{ data.name }}</strong>
                <div style="margin: 10px 0;">
                    <a href="/?test={{ id }}" class="test" style="text-decoration: none;">
                        <button class="test">TEST ET</button>
                    </a>
                    <form method="POST" style="display: inline;">
                        <input type="hidden" name="delete" value="{{ id }}">
                        <button type="submit" class="del">SİL</button>
                    </form>
                </div>
                <div class="links">
                    <a href="/m3u8/{{ id }}" target="_blank">📄 M3U8: {{ request.host_url }}m3u8/{{ id }}</a>
                    <a href="/stream/{{ id }}" target="_blank">▶️ STREAM: {{ request.host_url }}stream/{{ id }}</a>
                    <a href="/direct/{{ id }}" target="_blank">🔗 DİREKT: {{ request.host_url }}direct/{{ id }}</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, channels=CHANNELS, msg=msg, test_result=test_result)

def test_youtube_link(yt_url):
    """YouTube linkini test et ve detayları döndür"""
    result = []
    result.append(f"Test edilen URL: {yt_url}")
    result.append("-" * 50)
    
    # Yöntem 1: Direkt link al
    try:
        cmd = [
            "yt-dlp",
            "-g",
            "-f", "best",
            "--dump-json",
            "--no-warnings",
            yt_url
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        
        result.append(f"\n[YT-DLP Çıkış Kodu: {proc.returncode}]")
        
        if proc.stderr:
            result.append(f"\n[HATA ÇIKTISI]\n{proc.stderr[:1000]}")
        
        if proc.stdout:
            lines = proc.stdout.strip().split('\n')
            if lines:
                # Son satır genelde JSON olur
                try:
                    import json
                    info = json.loads(lines[-1])
                    result.append(f"\n[BAŞARILI - Video Bilgisi]")
                    result.append(f"Başlık: {info.get('title', 'N/A')}")
                    result.append(f"Format: {info.get('format', 'N/A')}")
                    result.append(f"Protokol: {info.get('protocol', 'N/A')}")
                    result.append(f"URL Uzunluğu: {len(info.get('url', ''))}")
                    result.append(f"\n[GERÇEK URL - İLK 200 KARAKTER]\n{info.get('url', 'Yok')[:200]}...")
                except:
                    result.append(f"\n[HAM ÇIKTILAR]\n{proc.stdout[:500]}")
        
    except Exception as e:
        result.append(f"\n[EXCEPTION]\n{str(e)}")
    
    return '\n'.join(result)

@app.route('/m3u8/<cid>')
def get_m3u8(cid):
    if cid not in CHANNELS:
        return "Kanal yok", 404
    
    base_url = request.host_url.rstrip('/')
    
    m3u8_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXTINF:-1,{CHANNELS[cid]['name']}
#EXT-X-STREAM-INF:BANDWIDTH=1280000
{base_url}/stream/{cid}
"""
    return Response(m3u8_content, mimetype='application/vnd.apple.mpegurl')

@app.route('/direct/<cid>')
def direct_stream(cid):
    """Direkt yönlendirme (En hızlı)"""
    if cid not in CHANNELS:
        return "Kanal yok", 404
    
    yt_url = CHANNELS[cid]['url']
    
    try:
        cmd = [
            "yt-dlp",
            "-g",
            "-f", "best",
            "--no-warnings",
            yt_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            direct_url = result.stdout.strip().split('\n')[0]
            return redirect(direct_url, code=302)
        else:
            return f"Direkt link alınamadı: {result.stderr}", 500
            
    except Exception as e:
        return f"Hata: {str(e)}", 500

@app.route('/stream/<cid>')
def proxy_stream(cid):
    """Proxy stream (FFmpeg ile)"""
    if cid not in CHANNELS:
        return "Kanal yok", 404
    
    yt_url = CHANNELS[cid]['url']
    
    # Önce linki al
    try:
        cmd_get = [
            "yt-dlp",
            "-g",
            "-f", "best",
            "--no-warnings",
            yt_url
        ]
        
        result = subprocess.run(cmd_get, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0 or not result.stdout.strip():
            return f"Link alınamadı: {result.stderr}", 500
        
        video_url = result.stdout.strip().split('\n')[0]
        
    except Exception as e:
        return f"Link hatası: {str(e)}", 500
    
    # FFmpeg ile stream et - HLS formatına zorla
    ffmpeg_cmd = [
        'ffmpeg',
        '-re',
        '-i', video_url,
        '-c:v', 'libx264',      # Video codec (H.264 - her yerde çalışır)
        '-c:a', 'aac',          # Audio codec
        '-preset', 'ultrafast', # Hızlı encoding
        '-tune', 'zerolatency', # Düşük gecikme
        '-f', 'mpegts',         # Transport stream
        '-mpegts_flags', '+initial_discontinuity',
        'pipe:1'
    ]
    
    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    def generate():
        # İlk veriyi bekle (FFmpeg başladı mı?)
        chunk = process.stdout.read(8192)
        if not chunk:
            err = process.stderr.read().decode()
            yield f"FFmpeg başlatılamadı: {err[:500]}".encode()
            return
        
        yield chunk
        try:
            while True:
                data = process.stdout.read(65536)
                if not data:
                    break
                yield data
        except:
            pass
        finally:
            if process.poll() is None:
                process.kill()
    
    return Response(stream_with_context(generate()), 
                   mimetype='video/mp2t',
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive'
                   })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, threaded=True)

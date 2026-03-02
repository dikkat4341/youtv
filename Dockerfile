FROM python:3.10-slim

# FFmpeg ve Git kur (YouTube için şart)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Flask kur
RUN pip install --no-cache-dir flask

# yt-dlp'nin EN SON sürümünü GitHub'dan çek (Zorunlu)
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

# Gunicorn YOK. Direkt Python başlatıyoruz.
# Bu sayede hafıza silinmez, eklediğin kanal gitmez.
CMD ["python", "app.py"]

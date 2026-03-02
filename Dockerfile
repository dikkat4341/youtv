FROM python:3.9-slim

# Temel araçları ve ffmpeg'i kur
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Flask ve Gunicorn kur
RUN pip install --no-cache-dir flask gunicorn

# ÖNEMLİ: yt-dlp'yi direkt GitHub'dan kur (En güncel sürüm için şart)
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

# Uygulamayı başlat
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "0", "--workers", "1", "app:app"]

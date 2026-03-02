# BURAYI DEĞİŞTİRDİK: 3.9 yerine 3.10 yaptık.
FROM python:3.10-slim

# Temel araçları, git ve ffmpeg'i kur
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Flask ve Gunicorn kur
RUN pip install --no-cache-dir flask gunicorn

# yt-dlp'yi GitHub'dan en güncel haliyle kur
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

# Uygulamayı başlat
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "0", "--workers", "1", "app:app"]

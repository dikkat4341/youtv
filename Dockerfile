FROM python:3.10-slim

# Gerekli araçlar
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Flask ve yt-dlp kur
RUN pip install --no-cache-dir flask
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

# ÖNEMLİ: Gunicorn YOK. Direkt Python var.
# Bu sayede eklediğin kanal silinmez, listede görünür.
CMD ["python", "app.py"]

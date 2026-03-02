FROM python:3.9-slim

# Gerekli sistem araçlarını ve ffmpeg kur
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dosyaları kopyala
COPY . .

# Python kütüphanelerini kur
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamayı başlat
CMD ["python", "app.py"]

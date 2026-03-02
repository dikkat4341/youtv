# Python tabanını al
FROM python:3.9-slim

# FFMPEG ve gerekli araçları kur (YouTube için şart)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Çalışma klasörü
WORKDIR /app

# Dosyaları kopyala
COPY . .

# Kütüphaneleri kur
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamayı başlat (Gunicorn ile)
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]

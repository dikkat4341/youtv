# Hafif ve güncel Python sürümü
FROM python:3.9-slim

# Sistem araçlarını kur (FFMPEG dahil)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Dosyaları kopyala
COPY . .

# Python kütüphanelerini kur
RUN pip install --no-cache-dir -r requirements.txt

# Gunicorn ayarı: 
# --timeout 0 (Yayın kesilmesin diye zaman aşımını kapatıyoruz)
# --workers 1 (Tek işlemci ile stabil çalışsın)
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "0", "--workers", "1", "app:app"]

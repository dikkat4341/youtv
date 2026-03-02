FROM python:3.9-slim

# Temel araçlar
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Kütüphaneleri kur
RUN pip install --no-cache-dir -r requirements.txt

# Zaman aşımını (timeout) kapatıyoruz ki yayın kesilmesin
CMD ["gunicorn", "-b", "0.0.0.0:10000", "--timeout", "0", "--workers", "1", "app:app"]

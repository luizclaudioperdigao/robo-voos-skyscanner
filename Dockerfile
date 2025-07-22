# Usa Python slim oficial
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema para Chromium funcionar
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    libpangocairo-1.0-0 libpango-1.0-0 libxcb1 libxfixes0 libxshmfence1 \
    libglib2.0-0 libfontconfig1 libxext6 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Instala navegadores do Playwright (Chromium)
RUN playwright install chromium

COPY . .

CMD ["python", "app.py"]

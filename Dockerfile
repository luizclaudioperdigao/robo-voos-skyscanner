# Usa imagem Python 3.11 completa (não slim)
FROM python:3.11

# Variáveis de ambiente para evitar arquivos .pyc e saída em buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Atualiza pacotes e instala bibliotecas necessárias para o Playwright + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libxcb1 \
    libxfixes3 \
    libxshmfence1 \
    libglib2.0-0 \
    libfontconfig1 \
    libxext6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho
WORKDIR /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Chromium via Playwright
RUN playwright install --with-deps chromium

# Copia o restante da aplicação
COPY . .

# Executa o bot
CMD ["python", "app.py"]

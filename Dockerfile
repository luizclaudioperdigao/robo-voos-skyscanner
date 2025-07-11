# Usa imagem oficial Python, versão slim para menos tamanho
FROM python:3.11-slim

# Define variáveis de ambiente para não gerar arquivos .pyc e para buffers de saída
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Atualiza o apt e instala dependências essenciais para algumas libs Python (ex: build-essential, gcc, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia requirements primeiro para usar cache do Docker na instalação
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para dentro do container
COPY . .

# Expõe a porta (se seu app tiver server, aqui não tem, mas fica de exemplo)
# EXPOSE 8080

# Comando para rodar o app
CMD ["python", "app.py"]

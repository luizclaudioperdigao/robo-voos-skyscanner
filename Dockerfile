# Usa a imagem oficial do Python slim
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia todos os arquivos do repositório para dentro do container
COPY . .

# Instala as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Comando padrão para rodar o robô em modo unbuffered (logs em tempo real)
CMD ["python", "-u", "robo_voos.py"]


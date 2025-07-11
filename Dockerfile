FROM python:3.11-slim

# Cria diretório de trabalho
WORKDIR /app

# Copia todos os arquivos do projeto
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando para rodar o robô
CMD ["python", "app.py"]


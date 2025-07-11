import os
import time
import requests
from bs4 import BeautifulSoup

# Configurações fixas
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"
MAX_PRECO = 2000
INTERVALO_MINUTOS = 10

# Pegando variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_mensagem(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Erro ao acessar Skyscanner: {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if not preco_span:
            print("⚠ Não foi possível encontrar o preço.")
            return None
        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        preco = float(texto_preco)
        return preco
    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None

def main():
    while True:
        print("🚀 Iniciando verificação de voos...")
        preco = buscar_voo()
        if preco is None:
            print("❌ Não foi possível obter o preço.")
        else:
            print(f"💰 Preço encontrado: R$ {preco:.2f}")
            if preco <= MAX_PRECO:
                mensagem = (
                    f"✈️ Voo barato encontrado!\n\n"
                    f"🔁 Ida: {DATA_IDA}\n"
                    f"🔁 Volta: {DATA_VOLTA}\n"
                    f"💰 Preço: R$ {preco:.2f}\n"
                    f"🔗 Link: https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/"
                )
                enviar_mensagem(mensagem)
            else:
                print("🔎 Preço acima do limite.")
        print(f"⏳ Aguardando {INTERVALO_MINUTOS} minutos...\n")
        time.sleep(INTERVALO_MINUTOS * 60)

if __name__ == "__main__":
    main()


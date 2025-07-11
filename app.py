import time
import requests
from bs4 import BeautifulSoup

# Configurações iniciais
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"
MAX_PRECO = 2000  # valor máximo em R$

# Dados do Telegram
TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"  # Substitua se necessário
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem(chat_id, texto):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"⚠️ Falha ao enviar mensagem: {resp.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Erro ao acessar Skyscanner: HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if not preco_span:
            print("⚠ Não foi possível encontrar o preço na página.")
            return None

        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        preco = float(texto_preco)
        return preco

    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None

def processar_comandos(offset):
    url = f"{TELEGRAM_API_URL}/getUpdates?timeout=10&offset={offset}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        for update in data.get("result", []):
            update_id = update["update_id"]
            message = update.get("message")
            if message:
                chat_id = message["chat"]["id"]
                texto = message.get("text", "").lower()

                if texto == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Use comandos para interagir.")
                elif texto == "/configuracoes":
                    msg = (
                        f"Configurações atuais:\n"
                        f"Origem: {ORIGEM}\n"
                        f"Destino: {DESTINO}\n"
                        f"Data ida: {DATA_IDA}\n"
                        f"Data volta: {DATA_VOLTA}\n"
                        f"Preço máximo: R$ {MAX_PRECO}"
                    )
                    enviar_mensagem(chat_id, msg)
            offset = update_id + 1
        return offset
    except Exception as e:
        print(f"Erro ao processar comandos: {e}")
        return offset

def main():
    print("🚀 Bot iniciado!")

    offset = 0
    while True:
        offset = processar_comandos(offset)
        preco = buscar_voo()

        if preco is None:
            print("❌ Não foi possível obter o preço.")
        else:
            print(f"💰 Preço encontrado: R$ {preco:.2f}")
            if preco <= MAX_PRECO:
                mensagem = (
                    f"✈️ Voo barato encontrado!\n"
                    f"Origem: {ORIGEM}\n"
                    f"Destino: {DESTINO}\n"
                    f"Data ida: {DATA_IDA}\n"
                    f"Data volta: {DATA_VOLTA}\n"
                    f"Preço: R$ {preco:.2f}\n"
                    f"🔗 https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/"
                )
                enviar_mensagem(TELEGRAM_CHAT_ID, mensagem)
            else:
                print("🔎 Preço acima do limite, nenhum alerta enviado.")

        print(f"⏳ Aguardando 10 minutos para próxima busca...\n")
        time.sleep(600)  # 10 minutos

if __name__ == "__main__":
    main()

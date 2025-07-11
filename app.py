import time
import requests
from bs4 import BeautifulSoup

# Configurações iniciais
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"
MAX_PRECO = 2000  # valor máximo em R$

# Telegram
TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem(chat_id, texto):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Erro ao enviar mensagem: {r.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Erro ao acessar Skyscanner: HTTP {r.status_code}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if not preco_span:
            print("⚠ Não achou o preço na página.")
            return None

        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(texto_preco)

    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None

def processar_comandos():
    offset = None
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            if offset:
                url += f"?offset={offset}&timeout=30"
            else:
                url += "?timeout=30"

            r = requests.get(url, timeout=40)
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue

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
        except Exception as e:
            print(f"Erro ao ler comandos: {e}")
        time.sleep(2)

def loop_busca_voos():
    while True:
        preco = buscar_voo()
        if preco is None:
            print("❌ Preço não encontrado.")
        else:
            print(f"💰 Preço atual: R$ {preco:.2f}")
            if preco <= MAX_PRECO:
                mensagem = (
                    f"✈️ Voo barato encontrado!\n"
                    f"Origem: {ORIGEM}\n"
                    f"Destino: {DESTINO}\n"
                    f"Ida: {DATA_IDA}\n"
                    f"Volta: {DATA_VOLTA}\n"
                    f"Preço: R$ {preco:.2f}\n"
                    f"🔗 https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/"
                )
                enviar_mensagem(TELEGRAM_CHAT_ID, mensagem)
            else:
                print("🔎 Preço acima do limite.")
        print("⏳ Esperando 10 min...\n")
        time.sleep(600)

def main():
    from threading import Thread
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

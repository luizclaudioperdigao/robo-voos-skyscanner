import time
import requests
from bs4 import BeautifulSoup
import os

# Configurações iniciais (pode ser alterado pelo Telegram)
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"
MAX_PRECO = 2000  # valor máximo em R$

# Telegram (usa variável de ambiente)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if TELEGRAM_TOKEN is None:
    raise ValueError("⚠️ A variável de ambiente TELEGRAM_TOKEN não está definida!")

TELEGRAM_CHAT_ID = "603459673"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem(chat_id, texto, inline_url=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }
    if inline_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "🔗 Comprar agora", "url": inline_url}]]
        }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"⚠️ Falha ao enviar mensagem: {resp.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {
        "User-Agent": "Mozilla/5.0"
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
    global ORIGEM, DESTINO, DATA_IDA, DATA_VOLTA, MAX_PRECO

    url = f"{TELEGRAM_API_URL}/getUpdates?timeout=10&offset={offset}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        for update in data.get("result", []):
            update_id = update["update_id"]
            message = update.get("message")
            if message:
                chat_id = message["chat"]["id"]
                texto = message.get("text", "").lower().strip()

                if texto == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Use os comandos:\n/start\n/configuracoes\n/atualizar_config")
                elif texto == "/configuracoes":
                    msg = (
                        f"<b>🔧 Configurações atuais:</b>\n"
                        f"• Origem: {ORIGEM}\n"
                        f"• Destino: {DESTINO}\n"
                        f"• Ida: {DATA_IDA}\n"
                        f"• Volta: {DATA_VOLTA}\n"
                        f"• Preço máximo: R$ {MAX_PRECO:.2f}"
                    )
                    enviar_mensagem(chat_id, msg)
                elif texto.startswith("/atualizar_config"):
                    try:
                        partes = texto.split()
                        if len(partes) == 6:
                            ORIGEM, DESTINO, DATA_IDA, DATA_VOLTA, MAX_PRECO = partes[1], partes[2], partes[3], partes[4], float(partes[5])
                            enviar_mensagem(chat_id, "✅ Configurações atualizadas com sucesso.")
                        else:
                            enviar_mensagem(chat_id, "Formato inválido.\nUse: /atualizar_config CNF MCO 2025-09-10 2025-09-20 2000")
                    except Exception:
                        enviar_mensagem(chat_id, "❌ Erro ao atualizar configurações.")
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
                link_voo = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/"
                mensagem = (
                    f"✈️ <b>Voo barato encontrado!</b>\n"
                    f"• Origem: {ORIGEM}\n"
                    f"• Destino: {DESTINO}\n"
                    f"• Ida: {DATA_IDA}\n"
                    f"• Volta: {DATA_VOLTA}\n"
                    f"• Preço: <b>R$ {preco:.2f}</b>"
                )
                enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, inline_url=link_voo)
            else:
                print("🔎 Preço acima do limite, nenhum alerta enviado.")

        print(f"⏳ Aguardando 60 segundos...\n")
        time.sleep(60)  # 1 minuto

if __name__ == "__main__":
    main()

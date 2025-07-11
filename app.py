import time
import requests
from bs4 import BeautifulSoup
from threading import Thread

# Configurações iniciais
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"
MAX_PRECO = 2000

# Telegram
TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Estado de atualização (1 usuário fixo)
ESTADO_ATUALIZACAO = None  # Ex: "ORIGEM", "DESTINO", etc.

def enviar_mensagem(chat_id, texto, botoes=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }
    if botoes:
        payload["reply_markup"] = {
            "inline_keyboard": botoes
        }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Erro ao enviar mensagem: {r.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Erro HTTP {r.status_code} ao acessar Skyscanner")
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if not preco_span:
            print("⚠ Não achou preço no HTML")
            return None
        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(texto_preco)
    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None

def processar_comandos():
    global ORIGEM, DESTINO, DATA_IDA, DATA_VOLTA, MAX_PRECO, ESTADO_ATUALIZACAO
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

                # Callback button
                if "callback_query" in update:
                    callback = update["callback_query"]
                    data = callback["data"]
                    chat_id = callback["message"]["chat"]["id"]

                    ESTADO_ATUALIZACAO = data  # Ex: "ORIGEM", "DESTINO"
                    perguntas = {
                        "ORIGEM": "✈️ Qual é a nova origem? (Ex: CNF)",
                        "DESTINO": "🏁 Qual é o novo destino? (Ex: MCO)",
                        "IDA": "📅 Qual é a nova data de ida? (Ex: 2025-09-15)",
                        "VOLTA": "📅 Qual é a nova data de volta? (Ex: 2025-10-05)",
                        "PRECO": "💸 Qual é o novo preço máximo? (Ex: 2000)"
                    }
                    enviar_mensagem(chat_id, perguntas[data])
                    continue

                # Mensagem normal
                message = update.get("message")
                if not message: continue
                chat_id = message["chat"]["id"]
                texto = message.get("text", "").strip()

                # Atualizando configuração conforme última seleção
                if ESTADO_ATUALIZACAO:
                    try:
                        if ESTADO_ATUALIZACAO == "ORIGEM":
                            ORIGEM = texto.upper()
                        elif ESTADO_ATUALIZACAO == "DESTINO":
                            DESTINO = texto.upper()
                        elif ESTADO_ATUALIZACAO == "IDA":
                            DATA_IDA = texto
                        elif ESTADO_ATUALIZACAO == "VOLTA":
                            DATA_VOLTA = texto
                        elif ESTADO_ATUALIZACAO == "PRECO":
                            MAX_PRECO = float(texto)
                        enviar_mensagem(chat_id, "✅ Configuração atualizada com sucesso!")
                    except:
                        enviar_mensagem(chat_id, "❌ Erro ao atualizar. Verifique o valor informado.")
                    ESTADO_ATUALIZACAO = None
                    continue

                # Comandos
                if texto == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Use /configuracoes para alterar.")
                elif texto == "/configuracoes":
                    msg = (
                        f"<b>🔧 Configurações atuais:</b>\n"
                        f"• Origem: {ORIGEM}\n"
                        f"• Destino: {DESTINO}\n"
                        f"• Ida: {DATA_IDA}\n"
                        f"• Volta: {DATA_VOLTA}\n"
                        f"• Preço máximo: R$ {MAX_PRECO:.2f}"
                    )
                    botoes = [
                        [
                            {"text": "✏️ Alterar Origem", "callback_data": "ORIGEM"},
                            {"text": "✏️ Alterar Destino", "callback_data": "DESTINO"}
                        ],
                        [
                            {"text": "📅 Alterar Ida", "callback_data": "IDA"},
                            {"text": "📅 Alterar Volta", "callback_data": "VOLTA"}
                        ],
                        [
                            {"text": "💸 Alterar Preço", "callback_data": "PRECO"}
                        ]
                    ]
                    enviar_mensagem(chat_id, msg, botoes)
        except Exception as e:
            print(f"Erro no loop de comandos: {e}")
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
        print("⏳ Aguardando 10 minutos...\n")
        time.sleep(600)

def main():
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

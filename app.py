import time
import requests
from bs4 import BeautifulSoup
from threading import Thread
import json
import os

CONFIG_PATH = "config.json"

def carregar_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    else:
        return {
            "origem": "CNF",
            "destino": "MIA",
            "data_ida": "2025-08-18",
            "data_volta": "2025-09-05",
            "max_preco": 99999,
            "busca_pausada": False,
            "estatisticas": {
                "buscas_feitas": 0,
                "ult_voo_baixo_preco": None
            }
        }

def salvar_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(CONFIG, f, indent=2)

CONFIG = carregar_config()
ESTADO_ATUALIZACAO = None

TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem(chat_id, texto, botoes=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }
    if botoes:
        payload["reply_markup"] = {"inline_keyboard": botoes}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Erro ao enviar mensagem: {r.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            enviar_mensagem(TELEGRAM_CHAT_ID, f"❌ Erro HTTP {r.status_code} ao acessar Skyscanner")
            return None

        html = r.text

        # Envia os primeiros 1000 caracteres do HTML para debug
        enviar_mensagem(TELEGRAM_CHAT_ID, f"<b>[DEBUG] HTML capturado (primeiros 1000 chars):</b>\n<pre>{html[:1000]}</pre>")

        soup = BeautifulSoup(html, "html.parser")
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")

        if not preco_span:
            enviar_mensagem(TELEGRAM_CHAT_ID, "⚠️ Não encontrou o preço no HTML. Talvez a página mudou ou o seletor está incorreto.")
            return None

        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        preco = float(texto_preco)
        return preco

    except Exception as e:
        enviar_mensagem(TELEGRAM_CHAT_ID, f"❌ Erro ao buscar preço: {e}")
        return None

def processar_comandos():
    global ESTADO_ATUALIZACAO
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

                if "callback_query" in update:
                    callback = update["callback_query"]
                    data = callback["data"]
                    chat_id = callback["message"]["chat"]["id"]

                    if data in ["PAUSAR", "CONTINUAR"]:
                        CONFIG["busca_pausada"] = (data == "PAUSAR")
                        salvar_config()
                        status = "⏸️ Busca pausada." if data == "PAUSAR" else "▶️ Busca retomada."
                        enviar_mensagem(chat_id, status)
                        continue

                    ESTADO_ATUALIZACAO = data
                    perguntas = {
                        "ORIGEM": "✈️ Qual é a nova origem? (Ex: CNF)",
                        "DESTINO": "🏁 Qual é o novo destino? (Ex: MCO)",
                        "IDA": "📅 Qual é a nova data de ida? (Ex: 2025-09-15)",
                        "VOLTA": "📅 Qual é a nova data de volta? (Ex: 2025-10-05)",
                        "PRECO": "💸 Qual é o novo preço máximo? (Ex: 2000)"
                    }
                    enviar_mensagem(chat_id, perguntas[data])
                    continue

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                texto = message.get("text", "").strip()

                if ESTADO_ATUALIZACAO:
                    try:
                        if ESTADO_ATUALIZACAO == "ORIGEM":
                            CONFIG["origem"] = texto.upper()
                        elif ESTADO_ATUALIZACAO == "DESTINO":
                            CONFIG["destino"] = texto.upper()
                        elif ESTADO_ATUALIZACAO == "IDA":
                            CONFIG["data_ida"] = texto
                        elif ESTADO_ATUALIZACAO == "VOLTA":
                            CONFIG["data_volta"] = texto
                        elif ESTADO_ATUALIZACAO == "PRECO":
                            CONFIG["max_preco"] = float(texto)
                        salvar_config()
                        enviar_mensagem(chat_id, "✅ Configuração atualizada!")
                    except:
                        enviar_mensagem(chat_id, "❌ Erro. Verifique o valor.")
                    ESTADO_ATUALIZACAO = None
                    continue

                if texto == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Use /configuracoes para editar.")
                elif texto == "/configuracoes":
                    msg = (
                        f"<b>🔧 Configurações:</b>\n"
                        f"• Origem: {CONFIG['origem']}\n"
                        f"• Destino: {CONFIG['destino']}\n"
                        f"• Ida: {CONFIG['data_ida']}\n"
                        f"• Volta: {CONFIG['data_volta']}\n"
                        f"• Máximo: R$ {CONFIG['max_preco']:.2f}\n"
                        f"• Busca pausada: {'Sim' if CONFIG['busca_pausada'] else 'Não'}"
                    )
                    botoes = [
                        [{"text": "✏️ Origem", "callback_data": "ORIGEM"},
                         {"text": "✏️ Destino", "callback_data": "DESTINO"}],
                        [{"text": "📅 Ida", "callback_data": "IDA"},
                         {"text": "📅 Volta", "callback_data": "VOLTA"}],
                        [{"text": "💸 Preço", "callback_data": "PRECO"}],
                        [{"text": "⏸️ Pausar", "callback_data": "PAUSAR"},
                         {"text": "▶️ Continuar", "callback_data": "CONTINUAR"}]
                    ]
                    enviar_mensagem(chat_id, msg, botoes)
                elif texto == "/status":
                    est = CONFIG.get("estatisticas", {})
                    ult = est.get("ult_voo_baixo_preco")
                    msg = (
                        f"<b>📊 Status:</b>\n"
                        f"• Pausado: {'Sim' if CONFIG['busca_pausada'] else 'Não'}\n"
                        f"• Buscas feitas: {est.get('buscas_feitas', 0)}\n"
                        f"• Último voo barato: {f'R$ {ult:.2f}' if ult else 'Nenhum ainda'}"
                    )
                    enviar_mensagem(chat_id, msg)
        except Exception as e:
            print(f"Erro no loop de comandos: {e}")
        time.sleep(2)

def loop_busca_voos():
    while True:
        if CONFIG.get("busca_pausada"):
            print("🔴 Busca pausada.")
        else:
            preco = buscar_voo()
            CONFIG["estatisticas"]["buscas_feitas"] += 1
            if preco is None:
                print("❌ Preço não encontrado.")
            else:
                print(f"💰 Preço atual: R$ {preco:.2f}")
                if preco <= CONFIG["max_preco"]:
                    CONFIG["estatisticas"]["ult_voo_baixo_preco"] = preco
                    salvar_config()
                    mensagem = (
                        f"✈️ <b>Voo barato!</b>\n"
                        f"📍 {CONFIG['origem']} → {CONFIG['destino']}\n"
                        f"🗓️ {CONFIG['data_ida']} até {CONFIG['data_volta']}\n"
                        f"💰 <b>R$ {preco:.2f}</b>"
                    )
                    link = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/"
                    botoes = [[{"text": "🔗 Comprar agora", "url": link}]]
                    enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, botoes)
                else:
                    print("🔎 Acima do limite.")
        salvar_config()
        print("⏳ Esperando 60s...\n")
        time.sleep(60)

def main():
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

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
            "destino": "MCO",
            "data_ida": "2025-09-15",
            "data_volta": "2025-10-05",
            "max_preco": 5000,
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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w")
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

                print(f"📩 Comando recebido: {texto}")
                print(f"📦 CONFIG atual: {CONFIG}")

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
                        enviar_mensagem(chat_id, "✅ Configuração atualizada com sucesso!")
                    except:
                        enviar_mensagem(chat_id, "❌ Erro ao atualizar. Verifique o valor informado.")
                    ESTADO_ATUALIZACAO = None
                    continue

                if texto == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Use /configuracoes para alterar.")
                elif texto == "/configuracoes":
                    try:
                        msg = (
                            f"<b>🔧 Configurações atuais:</b>\n"
                            f"• Origem: {CONFIG['origem']}\n"
                            f"• Destino: {CONFIG['destino']}\n"
                            f"• Ida: {CONFIG['data_ida']}\n"
                            f"• Volta: {CONFIG['data_volta']}\n"
                            f"• Preço máximo: R$ {CONFIG['max_preco']:.2f}\n"
                            f"• Busca pausada: {'Sim' if CONFIG['busca_pausada'] else 'Não'}"
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
                            ],
                            [
                                {"text": "⏸️ Pausar busca", "callback_data": "PAUSAR"},
                                {"text": "▶️ Continuar busca", "callback_data": "CONTINUAR"}
                            ]
                        ]
                        enviar_mensagem(chat_id, msg, botoes)
                    except Exception as e:
                        enviar_mensagem(chat_id, "❌ Erro ao exibir configurações.")
                        print(f"Erro no comando /configuracoes: {e}")
                elif texto == "/status":
                    est = CONFIG.get("estatisticas", {})
                    ult_voo = est.get("ult_voo_baixo_preco")
                    ult_voo_str = f"R$ {ult_voo:.2f}" if ult_voo else "Nenhum ainda"
                    msg = (
                        f"<b>📊 Status do Bot:</b>\n"
                        f"• Busca pausada: {'Sim' if CONFIG['busca_pausada'] else 'Não'}\n"
                        f"• Buscas feitas: {est.get('buscas_feitas', 0)}\n"
                        f"• Último voo barato: {ult_voo_str}"
                    )
                    enviar_mensagem(chat_id, msg)
                elif texto == "/pausar":
                    CONFIG["busca_pausada"] = True
                    salvar_config()
                    enviar_mensagem(chat_id, "⏸️ Busca pausada.")
                elif texto == "/continuar":
                    CONFIG["busca_pausada"] = False
                    salvar_config()
                    enviar_mensagem(chat_id, "▶️ Busca retomada.")
                else:
                    enviar_mensagem(chat_id, "❓ Comando não reconhecido. Use /configuracoes ou /status.")

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
                        f"✈️ <b>Voo barato encontrado!</b>\n"
                        f"📍 Origem: {CONFIG['origem']}\n"
                        f"📍 Destino: {CONFIG['destino']}\n"
                        f"🗓️ Ida: {CONFIG['data_ida']}\n"
                        f"🗓️ Volta: {CONFIG['data_volta']}\n"
                        f"💰 Preço: <b>R$ {preco:.2f}</b>"
                    )
                    link_voo = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/"
                    botoes = [[{"text": "🔗 Comprar agora", "url": link_voo}]]
                    enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, botoes)
                else:
                    print("🔎 Preço acima do limite.")

        salvar_config()
        print("⏳ Aguardando 1 minuto...\n")
        time.sleep(60)

def main():
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

import time
import requests
from bs4 import BeautifulSoup
from threading import Thread
import json
import os

CONFIG_PATH = "config.json"

def carregar_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config.json: {e}")
            config = {}
    else:
        config = {}

    # Valores padrão
    config.setdefault("origem", "CNF")
    config.setdefault("destino", "MCO")
    config.setdefault("data_ida", "2025-09-15")
    config.setdefault("data_volta", "2025-10-05")
    config.setdefault("max_preco", 2000.0)
    config.setdefault("busca_pausada", False)
    config.setdefault("estatisticas", {})
    config["estatisticas"].setdefault("buscas_feitas", 0)
    config["estatisticas"].setdefault("ult_voo_baixo_preco", None)

    return config

def salvar_config():
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar config.json: {e}")

CONFIG = carregar_config()
ESTADO_ATUALIZACAO = None

# Coloque seu token e chat id aqui
TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def enviar_mensagem(chat_id, texto, botoes=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if botoes:
        payload["reply_markup"] = {"inline_keyboard": botoes}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Erro ao enviar mensagem: {r.text}")
            return False
        return True
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
        return False

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Erro HTTP {r.status_code} ao acessar Skyscanner")
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Tentativa principal de encontrar o preço
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if preco_span:
            texto_preco = preco_span.get_text()
        else:
            # Fallback: procura por outro padrão possível (ajuste se quiser)
            texto_preco = None
            for span in soup.find_all("span"):
                txt = span.get_text()
                if txt and "R$" in txt:
                    texto_preco = txt
                    break
        
        if not texto_preco:
            print("⚠ Não achou preço no HTML")
            return None
        
        preco_str = texto_preco.replace("R$", "").replace(".", "").replace(",", ".").strip()
        preco_float = float(preco_str)
        return preco_float
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
            if not r.ok:
                print(f"Erro ao obter updates: {r.text}")
                time.sleep(5)
                continue

            updates = r.json().get("result", [])
            if not updates:
                # Nenhuma atualização
                time.sleep(2)
                continue

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
                    except Exception as e:
                        print(f"Erro ao atualizar configuração: {e}")
                        enviar_mensagem(chat_id, "❌ Erro. Verifique o valor informado.")
                    ESTADO_ATUALIZACAO = None
                    continue

                # Comandos gerais
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
                elif texto == "/pausar":
                    CONFIG["busca_pausada"] = True
                    salvar_config()
                    enviar_mensagem(chat_id, "⏸️ Busca pausada. O bot não fará buscas até você enviar /continuar.")
                elif texto == "/continuar":
                    CONFIG["busca_pausada"] = False
                    salvar_config()
                    enviar_mensagem(chat_id, "▶️ Busca retomada. O bot voltará a fazer buscas.")
                else:
                    enviar_mensagem(chat_id, "Comando não reconhecido. Use /configuracoes ou /status.")
        except Exception as e:
            print(f"Erro no loop de comandos: {e}")
            # Reseta offset para evitar loop travado
            offset = None
            time.sleep(5)

def loop_busca_voos():
    while True:
        if CONFIG.get("busca_pausada"):
            print("🔴 Busca pausada.")
        else:
            preco = buscar_voo()
            CONFIG["estatisticas"]["buscas_feitas"] = CONFIG["estatisticas"].get("buscas_feitas", 0) + 1
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
        print("⏳ Esperando 60 segundos...\n")
        time.sleep(60)

def main():
    print("🚀 Bot iniciado!")
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

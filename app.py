import time
import json
import os
from threading import Thread
from playwright.sync_api import sync_playwright
import requests

CONFIG_PATH = "config.json"

def carregar_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Configuração padrão (edite conforme desejar)
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

def salvar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

CONFIG = carregar_config()

# Carregar variáveis de ambiente com validação
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "❌ Variáveis de ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID precisam estar definidas."
    )

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
        print(f"[LOG] Enviando mensagem para chat_id={chat_id} com token início={TELEGRAM_TOKEN[:10]}...")
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Erro ao enviar mensagem: {r.status_code} - {r.text}")
        else:
            print(f"[LOG] Mensagem enviada com sucesso.")
    except Exception as e:
        print(f"❌ Exceção ao enviar mensagem: {e}")

def enviar_arquivo(chat_id, nome_arquivo):
    url = f"{TELEGRAM_API_URL}/sendDocument"
    try:
        with open(nome_arquivo, "rb") as file:
            files = {"document": file}
            data = {"chat_id": chat_id}
            r = requests.post(url, files=files, data=data)
            if not r.ok:
                print(f"Erro ao enviar arquivo: {r.text}")
            else:
                print("[LOG] Arquivo enviado com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar arquivo: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/?adults=1&children=0&adultsv2=1&cabinclass=economy"
    print(f"[LOG] Buscando voo em: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_selector("span.BpkText_bpk-text__NT07H", timeout=15000)

            html = page.content()
            with open("ultimo_html.html", "w", encoding="utf-8") as f:
                f.write(html)
            enviar_arquivo(TELEGRAM_CHAT_ID, "ultimo_html.html")

            preco_texto = page.query_selector("span.BpkText_bpk-text__NT07H")
            if not preco_texto:
                enviar_mensagem(TELEGRAM_CHAT_ID, "⚠️ Não encontrou o preço no HTML do Skyscanner.")
                browser.close()
                return None

            texto_preco = preco_texto.inner_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
            preco = float(texto_preco)
            browser.close()
            return preco

    except Exception as e:
        enviar_mensagem(TELEGRAM_CHAT_ID, f"❌ Erro ao buscar preço com Playwright: {e}")
        return None

def processar_comandos():
    ESTADO_ATUALIZACAO = None
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
                        salvar_config(CONFIG)
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
                        salvar_config(CONFIG)
                        enviar_mensagem(chat_id, "✅ Configuração atualizada!")
                    except Exception:
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
            print(f"❌ Erro no loop de comandos: {e}")
        time.sleep(2)

def loop_busca_voos():
    while True:
        if CONFIG.get("busca_pausada"):
            print("[LOG] 🔴 Busca pausada.")
        else:
            preco = buscar_voo()
            CONFIG["estatisticas"]["buscas_feitas"] = CONFIG["estatisticas"].get("buscas_feitas", 0) + 1
            if preco is None:
                print("[LOG] ❌ Preço não encontrado.")
            else:
                print(f"[LOG] 💰 Preço atual: R$ {preco:.2f}")
                if preco <= CONFIG["max_preco"]:
                    CONFIG["estatisticas"]["ult_voo_baixo_preco"] = preco
                    salvar_config(CONFIG)
                    mensagem = (
                        f"✈️ <b>Voo barato!</b>\n"
                        f"📍 {CONFIG['origem']} → {CONFIG['destino']}\n"
                        f"🗓️ {CONFIG['data_ida']} até {CONFIG['data_volta']}\n"
                        f"💰 <b>R$ {preco:.2f}</b>"
                    )
                    link = f"https://www.skyscanner.com.br/transport/flights/{CONFIG['origem']}/{CONFIG['destino']}/{CONFIG['data_ida']}/{CONFIG['data_volta']}/"
                    botoes = [[{"text": "🔗 Comprar agora", "url": link}]]
                    print(f"[LOG] Enviando mensagem para chat_id={TELEGRAM_CHAT_ID}")
                    enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, botoes)
                else:
                    print("[LOG] 🔎 Preço acima do limite.")
        salvar_config(CONFIG)
        time.sleep(60)

def main():
    print("[LOG] Iniciando bot de voos baratos.")
    Thread(target=processar_comandos, daemon=True).start()
    loop_busca_voos()

if __name__ == "__main__":
    main()

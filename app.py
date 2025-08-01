import os
import json
import time
import requests
from threading import Thread, Lock
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CONFIG_PATH = "config.json"
lock = Lock()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Variáveis de ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID são obrigatórias.")

def carregar_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "origem": "CNF",
        "destino": "MCO",
        "data_ida": "2025-09-10",
        "data_volta": "2025-09-24",
        "preco_max": 2000
    }

def salvar_config(config):
    with lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

def enviar_mensagem(chat_id, texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")

def enviar_arquivo(chat_id, caminho):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(caminho, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        try:
            r = requests.post(url, files=files, data=data, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"Erro ao enviar arquivo: {e}")

def extrair_preco(texto):
    try:
        return int(texto.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except:
        return None

def buscar_voo():
    config = carregar_config()
    url = f"https://www.skyscanner.com.br/transport/flights/{config['origem']}/{config['destino']}/{config['data_ida']}/{config['data_volta']}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page()
        try:
            print(f"Acessando: {url}")
            page.goto(url, timeout=60000)
            page.wait_for_selector("span:has-text('R$')", timeout=45000)
            textos = page.locator("span:has-text('R$')").all_inner_texts()
            precos = [extrair_preco(t) for t in textos if extrair_preco(t)]

            if precos:
                menor_preco = min(precos)
                print(f"Preço encontrado: R$ {menor_preco}")
                if menor_preco <= config['preco_max']:
                    mensagem = f"🔥 <b>Promoção encontrada!</b>\nR$ {menor_preco}\n\n<a href=\"{url}\">🔗 Comprar agora</a>"
                    enviar_mensagem(TELEGRAM_CHAT_ID, mensagem)
                else:
                    print("Preço acima do máximo definido.")
            else:
                print("⚠️ Nenhum preço encontrado na página.")
                page.screenshot(path="erro_scraping.png")
                enviar_arquivo(TELEGRAM_CHAT_ID, "erro_scraping.png")

        except PlaywrightTimeoutError as e:
            print(f"Timeout ao buscar voo: {e}")
            page.screenshot(path="timeout.png")
            enviar_arquivo(TELEGRAM_CHAT_ID, "timeout.png")
        except Exception as e:
            print(f"Erro inesperado: {e}")
        finally:
            browser.close()

def loop_busca():
    while True:
        buscar_voo()
        time.sleep(300)  # a cada 5 minutos

def responder_comandos():
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            if offset:
                url += f"?offset={offset}"
            resposta = requests.get(url, timeout=10).json()
            for update in resposta.get("result", []):
                offset = update["update_id"] + 1
                mensagem = update.get("message", {}).get("text", "")
                chat_id = update.get("message", {}).get("chat", {}).get("id")

                if mensagem == "/start":
                    enviar_mensagem(chat_id, "Olá! Sou seu bot de voos baratos. Estou monitorando ofertas para você ✈️")
        except Exception as e:
            print(f"Erro no loop de comandos: {e}")
        time.sleep(5)

if __name__ == "__main__":
    Thread(target=responder_comandos).start()
    Thread(target=loop_busca).start()

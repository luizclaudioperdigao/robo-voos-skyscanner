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
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Erro HTTP {r.status_code} ao acessar Skyscanner")
            return None

        # Salva o HTML bruto da página para análise
        with open("pagina_skyscanner.html", "w", encoding="utf-8") as f:
            f.write(r.text)

        soup = BeautifulSoup(r.text, "html.parser")

        # Estratégia 1 - Classe antiga (pouco confiável)
        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if preco_span:
            texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
            print(f"[html antigo] Preço encontrado: R$ {texto_preco}")
            return float(texto_preco)

        # Estratégia 2 - Buscar qualquer preço estilo R$ XXXX,XX
        possiveis_precos = soup.find_all(text=lambda t: "R$" in t and "," in t)
        for texto in possiveis_precos:
            try:
                valor = texto.strip().replace("R$", "").replace(".", "").replace(",", ".")
                preco = float(valor)
                print(f"[regex] Preço extraído: R$ {preco}")
                return preco
            except:
                continue

        print("❌ Nenhum preço encontrado no HTML.")
        return None

    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None


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
    loop_busca_voos()


if __name__ == "__main__":
    main()

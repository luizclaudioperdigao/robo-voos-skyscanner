import time
import requests
from bs4 import BeautifulSoup

# Configurações
ORIGEM = "CNF"
DESTINO = "MCO"
DATA_IDA = "2025-09-15"
DATA_VOLTA = "2025-10-05"  # 20 dias após a ida
MAX_PRECO = 2000  # Alerta se o valor estiver abaixo disso (em R$)
INTERVALO_SEGUNDOS = 10  # intervalo menor só para teste

# Telegram (token já atualizado)
TELEGRAM_TOKEN = "7478647827:AAGzL65chbpIeTut9z8PGJcSnjlJdC-aN3w"
TELEGRAM_CHAT_ID = "603459673"

def enviar_mensagem(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")

def buscar_voo():
    url = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/?adults=1&children=0&adultsv2=1&cabinclass=economy"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, proxies={"http": None, "https": None}, timeout=30)
        if response.status_code != 200:
            print(f"Erro ao acessar Skyscanner: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        preco_span = soup.find("span", class_="BpkText_bpk-text__NT07H")
        if not preco_span:
            print("⚠ Não foi possível encontrar o preço.")
            return None

        texto_preco = preco_span.get_text().replace("R$", "").replace(".", "").replace(",", ".").strip()
        preco = float(texto_preco)

        return preco

    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return None

def main():
    print("Robô de busca de voos iniciado!")
    for i in range(3):
        print(f"🚀 Iniciando verificação de voos no Skyscanner... (rodada {i+1})")

        preco = buscar_voo()

        if preco is None:
            print("❌ Não foi possível obter o preço.")
        else:
            print(f"💰 Preço encontrado: R$ {preco:.2f}")
            if preco <= MAX_PRECO:
                mensagem = (
                    f"✈️ Voo barato encontrado!\n\n"
                    f"🔁 Ida: {DATA_IDA}\n"
                    f"🔁 Volta: {DATA_VOLTA}\n"
                    f"💰 Preço: R$ {preco:.2f}\n"
                    f"🔗 Link: https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{DESTINO}/{DATA_IDA}/{DATA_VOLTA}/"
                )
                enviar_mensagem(mensagem)
            else:
                print("🔎 Preço acima do limite, nenhum alerta enviado.")

        print(f"⏳ Aguardando {INTERVALO_SEGUNDOS} segundos para próxima busca...\n")
        time.sleep(INTERVALO_SEGUNDOS)

    print("Execução de teste finalizada.")

if __name__ == "__main__":
    main()

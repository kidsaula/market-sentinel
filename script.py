import os
import yfinance as yf
import requests
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import pytz

import json

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        print(f"✅ Novo usuário salvo: {chat_id}")



def check_new_users():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url, timeout=10).json()


    for result in response.get("result", []):
        message = result.get("message")
        if message:
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text == "/start":
                save_user(chat_id)

# ===============================
# CONFIGURAÇÕES
# ===============================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Watchlist focada em IA (Semicondutores, Software, Cloud e Infraestrutura)
WATCHLIST = [
    "NVDA", "AMD", "AVGO", "TSM",  # Hardware/Chips
    "MSFT", "GOOGL", "AMZN", "META", # Big Tech / LLMs
    "PLTR", "AI", "SOUN", "BBAI",    # Software Puro de IA
    "ORCL", "IBM", "SNOW", "PLTR"    # Dados e Infraestrutura
]

# ===============================
# TIMESTAMP
# ===============================
def get_timestamp():
    tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

# ===============================
# INDICADORES
# ===============================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_asymmetry_score(data):
    rsi_score = (data['rsi'] - 50) / 50
    sma_score = - data['dist_sma20'] / 10
    high52_score = data['dist_high'] / 20

    W_RSI, W_SMA, W_HIGH = 0.4, 0.3, 0.3

    score = (
        W_RSI * rsi_score +
        W_SMA * sma_score +
        W_HIGH * high52_score
    )
    return round(score, 2)


def asymmetry_verdict(score):
    if score >= 0.40:
        return "🟢 COMPRA FORTE"
    elif score >= 0.15:
        return "🟡 COMPRA FRACA"
    elif score > -0.15:
        return "⚪ AGUARDAR"
    elif score > -0.40:
        return "🔴 VENDA FRACA"
    else:
        return "🔥 VENDA FORTE"

# ===============================
# DADOS DE MERCADO
# ===============================
def get_market_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="60d")

    current_price = stock.info.get("currentPrice") or stock.fast_info["last_price"]
    prev_close = stock.info.get("previousClose", current_price)

    sma_20 = hist["Close"].tail(20).mean()
    rsi = calculate_rsi(hist["Close"]).iloc[-1]
    high_52 = stock.info.get("fiftyTwoWeekHigh", current_price)

    return {
        "ticker": ticker,
        "price": current_price,
        "change": ((current_price - prev_close) / prev_close) * 100,
        "rsi": round(rsi, 2),
        "dist_sma20": ((current_price - sma_20) / sma_20) * 100,
        "dist_high": ((high_52 - current_price) / high_52) * 100
    }

# ===============================
# IA EXPLICATIVA
# ===============================

def get_ai_analysis(data):
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
Você é um especialista em psicologia de mercado e análise de fluxo (order flow). Sua missão é decifrar o "fear & greed" (medo e ganância) sobre o ativo {data['ticker']}.

DADOS TÉCNICOS ATUAIS:
- Preço: ${data['price']:.2f} ({data['change']:+.2f}%)
- RSI: {data['rsi']} (Sobrecompra >70 / Sobrevenda <30)
- Score de Assimetria: {data['asymmetry_score']}

INSTRUÇÕES DE ANÁLISE DE SENTIMENTO:
1) Identifique se o mercado está em estado de FOMO (euforia), Pânico, ou Fadiga.
2) Analise como o investidor humano médio está reagindo ao nível de preço atual: há resistência psicológica ou aceitação de alta?
3) Projete a durabilidade desse sentimento (ex: "exaustão de curto prazo" ou "tendência de manada sustentada").

REGRAS DE RESPOSTA:
- Use um tom direto, focado no comportamento dos players.
- OBRIGATÓRIO: Liste ao final as fontes de dados consultadas (ex: Yahoo Finance, Bloomberg, Reuters, Sentiment Analysis Tools).
- Idioma: Português.

ESTRUTURA DA RESPOSTA:
- VEREDITO: [Status]
- ANÁLISE DE SENTIMENTO: [Máximo 3 frases focadas no fator humano e duração do viés]
- FONTES: [Lista de sites/terminais consultados]
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "Você é um analista de sentimento de mercado focado no comportamento humano e fluxos institucionais."},
                  {"role": "user", "content": prompt}],
        temperature=0.5 # Menor temperatura para evitar alucinações nas fontes
    )

    return completion.choices[0].message.content.strip()

# ===============================
# TELEGRAM
# ===============================
def send_telegram(message):
    users = load_users()
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    for chat_id in users:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            requests.post(url, json=payload, timeout=10)
            print(f"📨 Enviado para {chat_id}")
        except Exception as e:
            print(f"❌ Erro para {chat_id}: {e}")

# ===============================
# EXECUÇÃO
# ===============================
check_new_users()
print(f"🚀 Iniciando monitoramento de {len(WATCHLIST)} ativos...")

for ticker in WATCHLIST:
    try:
        print(f"🔎 Analisando {ticker}...")
        dados = get_market_data(ticker)

        timestamp = get_timestamp()

        dados["asymmetry_score"] = calculate_asymmetry_score(dados)
        quant_verdict = asymmetry_verdict(dados["asymmetry_score"])

        ai_comment = get_ai_analysis(dados)

        msg = f"📊 *ATIVO: {ticker}*\n"
        msg += f"🕒 Data/Hora: {timestamp}\n"
        msg += f"💰 Preço: ${dados['price']:.2f} ({dados['change']:+.2f}%)\n"
        msg += f"🌡️ RSI: {dados['rsi']} | 📏 Média 20d: {dados['dist_sma20']:+.2f}%\n"
        msg += f"📐 Score Assimetria: *{dados['asymmetry_score']}* → {quant_verdict}\n\n"
        msg += f"*Comentário IA:*\n{ai_comment}"

        send_telegram(msg)
        print(f"✅ {ticker} concluído.")

    except Exception as e:
        print(f"❌ Erro em {ticker}: {e}")

print("🏁 Processo finalizado.")
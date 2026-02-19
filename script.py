import os
import yfinance as yf
import requests
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import pytz

# ===============================
# CONFIGURAÇÕES
# ===============================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

WATCHLIST = ["NVDA"]

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
Você é um analista conservador profissional com foco em dados e notícias.

ATIVO: {data['ticker']}

DADOS TÉCNICOS:
- Preço atual: ${data['price']:.2f} ({data['change']:+.2f}%)
- RSI (14d): {data['rsi']}
- Distância da Média 20d: {data['dist_sma20']:.2f}%
- Distância da Máxima 52 semanas: {data['dist_high']:.2f}%
- Score de Assimetria: {data['asymmetry_score']}

INSTRUÇÃO DE CONTEXTO:
1) Analise as notícias mais atuais relacionadas a este ativo (mercado, setor, relatórios, sentimento dos investidores).
2) Avalie o sentimento do mercado financeiro em relação a esta ação no curto prazo.
3) Diga se há otimismo, pessimismo ou neutralidade dominante e por quanto tempo esse sentimento pode persistir no curto prazo.
4) Compare o contexto de notícias com os dados técnicos.

REGRAS OBRIGATÓRIAS:
- Use os dados técnicos para formar uma base.
- Considere o contexto de notícias e sentimento de mercado como suporte ou impedimento ao veredito.
- Limite sua resposta a no máximo 3 frases.

TAREFA:
Dê o VEREDITO: [COMPRA FORTE / COMPRA FRACA / AGUARDAR / VENDA FRACA / VENDA FORTE]

Explique em no máximo 3 frases o raciocínio, incluindo sentimento do mercado e indicação de duração do otimismo ou pessimismo no curto prazo.
Responda em Português.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return completion.choices[0].message.content.strip()

# ===============================
# TELEGRAM
# ===============================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload, timeout=10).raise_for_status()
        print("📨 Enviado com sucesso.")
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")

# ===============================
# EXECUÇÃO
# ===============================
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
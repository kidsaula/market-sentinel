import os
import yfinance as yf
import requests
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

# Carrega do .env (local) ou do ambiente (GitHub)
load_dotenv()

# --- CONFIGURAÇÕES ---
# --- CONFIGURAÇÕES (Preencha com seus dados reais) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Lista de ativos para monitorar
WATCHLIST = ["NVDA", "AAPL", "TSLA", "MSFT", "AMZN"]

from urllib.parse import urljoin # Adicione isso no topo do arquivo junto com os outros imports

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="60d")
    
    # Preço e Fechamento Anterior
    current_price = stock.info.get('currentPrice') or stock.fast_info['last_price']
    prev_close = stock.info.get('previousClose')
    
    # Médias e RSI
    sma_20 = hist['Close'].tail(20).mean()
    rsi = calculate_rsi(hist['Close']).iloc[-1]
    high_52 = stock.info.get('fiftyTwoWeekHigh', current_price)
    
    return {
        "ticker": ticker,
        "price": current_price,
        "change": ((current_price - prev_close) / prev_close) * 100,
        "rsi": round(rsi, 2),
        "dist_sma20": ((current_price - sma_20) / sma_20) * 100,
        "dist_high": ((high_52 - current_price) / high_52) * 100,
        "info": stock.info.get('longBusinessSummary', '')[:300]
    }

def get_ai_analysis(data):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"""
Atue como Trader de Elite. Analise {data['ticker']}:
- Preço: ${data['price']:.2f} ({data['change']:+.2f}%)
- RSI (14d): {data['rsi']} (Abaixo de 30=Barato, Acima de 70=Caro)
- Dist. Média 20d: {data['dist_sma20']:.2f}%
- Dist. Máxima 52 sem: {data['dist_high']:.2f}%

TAREFA:
Dê o VEREDITO: [COMPRA FORTE / AGUARDAR / VENDA]

1. Com base no RSI e Dist. Média, o ativo está em zona de exaustão ou oportunidade?

2. Justifique em 2 frases o veredito.
Responda em Português.
"""
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def send_telegram(message):
    # Esta é a forma mais segura de montar a URL sem erro de barras
    base_url = "https://api.telegram.org"
    endpoint = f"bot{TELEGRAM_TOKEN}/sendMessage"
    url = f"{base_url}/{endpoint}"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        # O timeout evita que o script fique travado se a internet oscilar
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("🚀 Sucesso! Verifique seu Telegram, Priscilla.")
    except Exception as e:
        print(f"❌ Erro ao enviar para o Telegram: {e}")
        print(f"DEBUG - URL tentada: {url}") # Isso vai nos mostrar exatamente o que deu errado

# --- EXECUÇÃO EM MASSA ---
print(f"🚀 Iniciando monitoramento de {len(WATCHLIST)} ativos...")

for ticker in WATCHLIST:
    try:
        print(f"Analisando {ticker}...")
        dados = get_market_data(ticker)
        analise = get_ai_analysis(dados)
        
        # Montagem do relatório elegante
        msg = f"📊 *ATIVO: {ticker}*\n"
        msg += f"💰 Preço: ${dados['price']:.2f} ({dados['change']:+.2f}%)\n"
        msg += f"🌡️ RSI: {dados['rsi']} | 📏 Média 20d: {dados['dist_sma20']:+.2f}%\n\n"
        msg += f"*Veredito IA:*\n{analise}"
        
        send_telegram(msg)
        print(f"✅ {ticker} enviado!")
        
    except Exception as e:
        print(f"❌ Erro em {ticker}: {e}")

print("🏁 Processo concluído!")

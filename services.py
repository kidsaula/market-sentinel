import requests
import yfinance as yf
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY
from concurrent.futures import ThreadPoolExecutor

def get_market_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="60d")
    info = stock.info
    
    current_price = info.get("currentPrice") or stock.fast_info["last_price"]
    prev_close = info.get("previousClose", current_price)
    
    return {
        "ticker": ticker,
        "price": current_price,
        "change": ((current_price - prev_close) / prev_close) * 100,
        "close_history": hist["Close"],
        "high_52": info.get("fiftyTwoWeekHigh", current_price)
    }

def get_ai_analysis(data):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"Analise o sentimento de {data['ticker']}... RSI: {data['rsi']}, Score: {data['asymmetry_score']}" # Resumido
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "Analista de sentimento profissional."},
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )
    return completion.choices[0].message.content.strip()

def send_single_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro no chat {chat_id}: {e}")

def broadcast_telegram(message, user_list):
    # Envia para todos os usuários simultaneamente
    with ThreadPoolExecutor(max_workers=10) as executor:
        for chat_id in user_list:
            executor.submit(send_single_message, chat_id, message)

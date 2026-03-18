import requests
import yfinance as yf
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY
from concurrent.futures import ThreadPoolExecutor

def fetch_news(ticker):
    """
    Retorna lista de notícias do ticker via yfinance.
    Cada item: {"uuid": str, "title": str, "link": str}
    Compatível com a nova estrutura aninhada em item['content'].
    """
    stock = yf.Ticker(ticker)
    raw = stock.news or []
    results = []
    for item in raw:
        # Nova estrutura: dados dentro de item['content']
        content = item.get("content") or item
        uuid = content.get("id") or item.get("id", "")
        title = content.get("title", "")
        link = (
            content.get("canonicalUrl", {}).get("url")
            or content.get("clickThroughUrl", {}).get("url")
            or item.get("link", "")
        )
        if title:
            results.append({"uuid": uuid, "title": title, "link": link})
    return results

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
    
    # Restaurando o prompt original rigoroso
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
        messages=[
            {"role": "system", "content": "Você é um analista de sentimento de mercado focado no comportamento humano e fluxos institucionais."},
            {"role": "user", "content": prompt}
        ],
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

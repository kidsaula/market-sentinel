import pandas as pd
from groq import Groq
from config import GROQ_API_KEY

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_asymmetry_score(data):
    """
    Baseado em RSI, distância da média de 20 dias e distância do topo histórico (52 semanas).
    """
    rsi_score = (data['rsi'] - 50) / 50
    sma_score = - data['dist_sma20'] / 10
    high52_score = data['dist_high'] / 20

    # Pesos dos indicadores
    W_RSI, W_SMA, W_HIGH = 0.4, 0.3, 0.3

    score = (W_RSI * rsi_score + W_SMA * sma_score + W_HIGH * high52_score)
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

def classify_news_consensus(ticker, headlines):
    """
    Envia todos os títulos novos de um ticker para o LLaMA e retorna
    (impacto_geral, consenso) onde impacto_geral é 'ALTO', 'MÉDIO' ou 'BAIXO'.
    """
    client = Groq(api_key=GROQ_API_KEY)
    lista = "\n".join(f"- {h}" for h in headlines)
    prompt = f"""Você é um analista financeiro sênior. Avalie o conjunto de notícias abaixo sobre o ativo {ticker} e dê um consenso geral.

NOTÍCIAS:
{lista}

RESPONDA EXATAMENTE neste formato (sem texto extra):
IMPACTO: [ALTO, MÉDIO ou BAIXO]
CONSENSO: [2 a 3 frases resumindo o sentimento geral do noticiário e o que o investidor deve observar]"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    response = completion.choices[0].message.content.strip()

    impacto = "BAIXO"
    consenso = ""
    for line in response.splitlines():
        if line.startswith("IMPACTO:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("ALTO", "MÉDIO", "BAIXO"):
                impacto = val
        elif line.startswith("CONSENSO:"):
            consenso = line.split(":", 1)[1].strip()
    return impacto, consenso

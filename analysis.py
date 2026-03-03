import pandas as pd

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

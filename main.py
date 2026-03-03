import pytz
from datetime import datetime
from config import WATCHLIST
import database as db
import services as sv
import analysis as an  
from concurrent.futures import ThreadPoolExecutor

def process_ticker(ticker):
    try:
        # 1. Coleta de dados (via services.py)
        raw_data = sv.get_market_data(ticker)
        hist_close = raw_data["close_history"]
        
        # 2. Cálculos Técnicos Exatos (Igual ao original)
        current_price = raw_data["price"]
        sma_20 = hist_close.tail(20).mean()
        rsi_series = an.calculate_rsi(hist_close)
        rsi_value = round(rsi_series.iloc[-1], 2)
        
        # Cálculos de distância para o Score e para a Mensagem
        dist_sma20 = ((current_price - sma_20) / sma_20) * 100
        dist_high = ((raw_data["high_52"] - current_price) / raw_data["high_52"]) * 100

        # Montagem do dicionário para a IA e para o Score
        data_for_analysis = {
            "ticker": ticker,
            "price": current_price,
            "change": raw_data["change"],
            "rsi": rsi_value,
            "dist_sma20": dist_sma20,
            "dist_high": dist_high,
            "asymmetry_score": 0 # placeholder
        }

        # 3. Gerar Score e Veredito (via analysis.py)
        data_for_analysis["asymmetry_score"] = an.calculate_asymmetry_score(data_for_analysis)
        quant_verdict = an.asymmetry_verdict(data_for_analysis["asymmetry_score"])

        # 4. IA (com o Prompt restaurado no services.py)
        ai_comment = sv.get_ai_analysis(data_for_analysis)

        # 5. Formatação da Mensagem (IDÊNTICA ao original)
        timestamp = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
        
        msg = f"📊 *ATIVO: {ticker}*\n"
        msg += f"🕒 Data/Hora: {timestamp}\n"
        msg += f"💰 Preço: ${current_price:.2f} ({raw_data['change']:+.2f}%)\n"
        msg += f"🌡️ RSI: {rsi_value} | 📏 Média 20d: {dist_sma20:+.2f}%\n"
        msg += f"📐 Score Assimetria: *{data_for_analysis['asymmetry_score']}* → {quant_verdict}\n\n"
        msg += f"*Comentário IA:*\n{ai_comment}"

        # 6. Envio
        users = db.load_users()
        sv.broadcast_telegram(msg, users)
        print(f"✅ {ticker} enviado com sucesso.")

    except Exception as e:
        print(f"❌ Erro em {ticker}: {e}")

if __name__ == "__main__":
    db.check_new_users() # Atualiza lista de inscritos
    print(f"🚀 Analisando {len(WATCHLIST)} ativos em paralelo...")
    
    # Roda a análise de cada ticker em paralelo para ganhar tempo
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_ticker, WATCHLIST)

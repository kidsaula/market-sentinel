import pytz
from datetime import datetime
from config import WATCHLIST
import database as db
import services as sv
import analysis as an  
from concurrent.futures import ThreadPoolExecutor

def process_ticker(ticker):
    try:
        # 1. Coleta
        raw_data = sv.get_market_data(ticker)
        
        # 2. Processamento (Análise técnica)
        rsi = an.calculate_rsi(raw_data["close_history"])
        data = {
            **raw_data,
            "rsi": round(rsi.iloc[-1], 2),
            "dist_sma20": ((raw_data["price"] - raw_data["close_history"].tail(20).mean()) / raw_data["close_history"].tail(20).mean()) * 100,
            "dist_high": ((raw_data["high_52"] - raw_data["price"]) / raw_data["high_52"]) * 100
        }
        
        data["asymmetry_score"] = an.calculate_asymmetry_score(data)
        verdict = an.asymmetry_verdict(data["asymmetry_score"])
        
        # 3. IA
        ai_comment = sv.get_ai_analysis(data)
        
        # 4. Formatação e Envio
        timestamp = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%H:%M")
        msg = (f"📊 *{ticker}* | ${data['price']:.2f} ({data['change']:+.2f}%)\n"
               f"📐 Score: *{data['asymmetry_score']}* -> {verdict}\n\n"
               f"{ai_comment}")
        
        users = db.load_users()
        sv.broadcast_telegram(msg, users)
        print(f"✅ {ticker} processado.")
        
    except Exception as e:
        print(f"❌ Erro em {ticker}: {e}")

if __name__ == "__main__":
    db.check_new_users() # Atualiza lista de inscritos
    print(f"🚀 Analisando {len(WATCHLIST)} ativos em paralelo...")
    
    # Roda a análise de cada ticker em paralelo para ganhar tempo
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_ticker, WATCHLIST)

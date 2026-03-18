import argparse
import pytz
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import WATCHLIST
import database as db
import services as sv
import analysis as an


# ── MODO REPORT ──────────────────────────────────────────────────────────────

def process_ticker(ticker):
    try:
        raw_data = sv.get_market_data(ticker)
        hist_close = raw_data["close_history"]

        current_price = raw_data["price"]
        sma_20 = hist_close.tail(20).mean()
        rsi_value = round(an.calculate_rsi(hist_close).iloc[-1], 2)

        dist_sma20 = ((current_price - sma_20) / sma_20) * 100
        dist_high = ((raw_data["high_52"] - current_price) / raw_data["high_52"]) * 100

        data_for_analysis = {
            "ticker": ticker,
            "price": current_price,
            "change": raw_data["change"],
            "rsi": rsi_value,
            "dist_sma20": dist_sma20,
            "dist_high": dist_high,
            "asymmetry_score": 0,
        }

        data_for_analysis["asymmetry_score"] = an.calculate_asymmetry_score(data_for_analysis)
        quant_verdict = an.asymmetry_verdict(data_for_analysis["asymmetry_score"])
        ai_comment = sv.get_ai_analysis(data_for_analysis)

        timestamp = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")

        msg = f"📊 *ATIVO: {ticker}*\n"
        msg += f"🕒 Data/Hora: {timestamp}\n"
        msg += f"💰 Preço: ${current_price:.2f} ({raw_data['change']:+.2f}%)\n"
        msg += f"🌡️ RSI: {rsi_value} | 📏 Média 20d: {dist_sma20:+.2f}%\n"
        msg += f"📐 Score Assimetria: *{data_for_analysis['asymmetry_score']}* → {quant_verdict}\n\n"
        msg += f"*Comentário IA:*\n{ai_comment}"

        users = db.load_users()
        sv.broadcast_telegram(msg, users)
        print(f"✅ {ticker} enviado com sucesso.")

    except Exception as e:
        print(f"❌ Erro em {ticker}: {e}")


def run_report():
    db.check_new_users()
    print(f"🚀 Analisando {len(WATCHLIST)} ativos em paralelo...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_ticker, WATCHLIST)


# ── MODO NEWS ────────────────────────────────────────────────────────────────

def process_news(ticker, seen_ids):
    """
    Busca notícias do ticker, filtra as já vistas, pede um consenso geral à IA
    e envia UMA única mensagem no Telegram se o impacto consolidado for ALTO.
    Retorna set com os UUIDs novos processados.
    """
    new_ids = set()
    try:
        news_list = sv.fetch_news(ticker)
        new_news = [n for n in news_list if n["uuid"] and n["uuid"] not in seen_ids]

        if not new_news:
            return new_ids

        new_ids = {n["uuid"] for n in new_news}
        headlines = [n["title"] for n in new_news]

        impacto, consenso = an.classify_news_consensus(ticker, headlines)
        print(f"  [{ticker}] {impacto} — {len(new_news)} notícia(s) nova(s)")

        if impacto == "ALTO":
            links = "\n".join(f"• [{n['title'][:60]}]({n['link']})" for n in new_news)
            msg = (
                f"🚨 *ALERTA DE NOTÍCIAS — {ticker}*\n\n"
                f"⚡ *Impacto Geral:* {impacto}\n"
                f"🧠 *Consenso IA:* {consenso}\n\n"
                f"📰 *Notícias ({len(new_news)}):*\n{links}"
            )
            users = db.load_users()
            sv.broadcast_telegram(msg, users)
            print(f"  🚨 Alerta consolidado enviado para {ticker}.")

    except Exception as e:
        print(f"❌ Erro ao processar notícias de {ticker}: {e}")

    return new_ids


def run_news():
    print(f"📡 Sentinel News — monitorando {len(WATCHLIST)} ativos...")
    log = db.load_news_log()
    seen_ids = set(log.keys())
    all_new_ids = set()

    for ticker in WATCHLIST:
        new_ids = process_news(ticker, seen_ids)
        all_new_ids.update(new_ids)

    if all_new_ids:
        db.save_news_log(log, all_new_ids)
        print(f"💾 {len(all_new_ids)} nova(s) notícia(s) registrada(s) no log.")
    else:
        print("✅ Nenhuma notícia nova encontrada.")


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Sentinel")
    parser.add_argument(
        "--mode",
        choices=["report", "news"],
        default="report",
        help="report: análise técnica | news: monitoramento de notícias",
    )
    args = parser.parse_args()

    if args.mode == "report":
        run_report()
    else:
        run_news()

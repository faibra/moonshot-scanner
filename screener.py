import requests
import yfinance as yf
from bs4 import BeautifulSoup
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

HARAM_SECTORS = [
    "Financial Services", "Banks", "Insurance",
    "Tobacco", "Beverages—Brewers", "Aerospace & Defense"
]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    })

def get_finviz_tickers():
    url = (
        "https://finviz.com/screener.ashx?"
        "v=111&f=cap_micro,sh_float_u20,"
        "sh_short_o10,ta_perf_dup,sh_avgvol_o300&o=-change"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    
    tickers = []
    for a in soup.select("a.screener-link-primary"):
        tickers.append(a.text.strip())
    return list(set(tickers))[:15]

def analyze(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get("sector", "")
        
        # Shariah filter
        if any(h in sector for h in HARAM_SECTORS):
            return None
        
        short_pct = info.get("shortPercentOfFloat", 0) or 0
        float_shares = info.get("floatShares", 0) or 0
        price = info.get("currentPrice", 0) or 0
        name = info.get("shortName", ticker)
        
        return {
            "ticker": ticker,
            "name": name,
            "price": price,
            "short_pct": round(short_pct * 100, 1),
            "float_m": round(float_shares / 1e6, 1),
            "sector": sector
        }
    except:
        return None

def main():
    send_telegram("🔍 *Running morning moonshot scan...*")
    tickers = get_finviz_tickers()
    
    if not tickers:
        send_telegram("⚠️ No tickers found — Finviz may have blocked the scan.")
        return
    
    results = []
    for t in tickers:
        data = analyze(t)
        if data:
            results.append(data)
    
    if not results:
        send_telegram("✅ Scan complete. No Shariah-compliant setups today.")
        return
    
    # Sort by short interest
    results.sort(key=lambda x: x["short_pct"], reverse=True)
    
    msg = "🚀 *Moonshot Watchlist — Today*\n\n"
    for r in results[:8]:
        msg += (
            f"*{r['ticker']}* — {r['name']}\n"
            f"💰 Price: ${r['price']}\n"
            f"📉 Short: {r['short_pct']}%\n"
            f"🔢 Float: {r['float_m']}M\n"
            f"🏭 Sector: {r['sector']}\n"
            f"[📊 Chart](https://finviz.com/quote.ashx?t={r['ticker']})\n\n"
        )
    
    send_telegram(msg)

if __name__ == "__main__":
    main()

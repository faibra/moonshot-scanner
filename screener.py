import requests
import yfinance as yf
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

def get_tickers():
    # Pull from 3 Yahoo Finance free screeners
    screeners = [
        "small_cap_gainers",
        "most_shorted_stocks",
        "day_gainers"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    tickers = []
    for screen in screeners:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v1/finance/screener/"
                f"predefined/saved?formatted=false&scrIds={screen}"
                f"&count=25&region=US&lang=en-US"
            )
            r = requests.get(url, headers=headers, timeout=10)
            quotes = r.json()["finance"]["result"][0]["quotes"]
            tickers.extend([q["symbol"] for q in quotes])
        except Exception as e:
            print(f"Screener {screen} failed: {e}")
            continue

    return list(set(tickers))

def analyze(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")

        # Shariah filter
        if any(h in sector for h in HARAM_SECTORS):
            return None

        short_pct = (info.get("shortPercentOfFloat") or 0) * 100
        float_shares = info.get("floatShares") or 0
        price = info.get("currentPrice") or 0
        mkt_cap = info.get("marketCap") or 0
        name = info.get("shortName", ticker)

        # Only micro/small caps under $500M
        if mkt_cap > 500_000_000:
            return None

        # Need meaningful short interest
        if short_pct < 8:
            return None

        return {
            "ticker": ticker,
            "name": name,
            "price": price,
            "short_pct": round(short_pct, 1),
            "float_m": round(float_shares / 1e6, 1),
            "mkt_cap_m": round(mkt_cap / 1e6, 1),
            "sector": sector
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def main():
    send_telegram("🔍 *Running morning moonshot scan...*")

    tickers = get_tickers()
    print(f"Found {len(tickers)} tickers to analyze")

    if not tickers:
        send_telegram("⚠️ Could not retrieve tickers. Yahoo Finance may be down.")
        return

    results = []
    for t in tickers:
        data = analyze(t)
        if data:
            results.append(data)

    if not results:
        send_telegram("✅ Scan complete — no Shariah-compliant setups found today.")
        return

    # Sort by highest short interest first
    results.sort(key=lambda x: x["short_pct"], reverse=True)

    msg = "🚀 *Moonshot Watchlist — Today*\n\n"
    for r in results[:8]:
        msg += (
            f"*{r['ticker']}* — {r['name']}\n"
            f"💰 Price: ${r['price']}\n"
            f"📉 Short: {r['short_pct']}%\n"
            f"🔢 Float: {r['float_m']}M shares\n"
            f"📊 Mkt Cap: ${r['mkt_cap_m']}M\n"
            f"🏭 Sector: {r['sector']}\n"
            f"[📈 Chart](https://finviz.com/quote.ashx?t={r['ticker']})\n\n"
        )

    send_telegram(msg)
    print("Done.")

if __name__ == "__main__":
    main()

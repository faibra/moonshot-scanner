import requests
import yfinance as yf
import os
import datetime

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
    screeners = [
        "small_cap_gainers",
        "most_shorted_stocks",
        "day_gainers"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
    return list(set(tickers))

def score_stock(short_pct, float_m, upside_pct, analyst_count, mkt_cap_m):
    score = 0
    if short_pct >= 20:
        score += 3
    elif short_pct >= 10:
        score += 2
    if float_m < 10:
        score += 3
    elif float_m < 20:
        score += 2
    if upside_pct >= 50:
        score += 3
    elif upside_pct >= 20:
        score += 2
    if analyst_count >= 3:
        score += 1
    if mkt_cap_m < 100:
        score += 1
    return score

def get_star_rating(score):
    if score >= 8:
        return "⭐⭐⭐⭐⭐ Strong Buy"
    elif score >= 6:
        return "⭐⭐⭐⭐ Buy"
    elif score >= 4:
        return "⭐⭐⭐ Watch"
    else:
        return None

def analyze(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")

        if any(h in sector for h in HARAM_SECTORS):
            return None

        short_pct = (info.get("shortPercentOfFloat") or 0) * 100
        float_shares = info.get("floatShares") or 0
        price = info.get("currentPrice") or 0
        mkt_cap = info.get("marketCap") or 0
        name = info.get("shortName", ticker)
        target_mean = info.get("targetMeanPrice") or 0
        target_high = info.get("targetHighPrice") or 0
        target_low = info.get("targetLowPrice") or 0
        analyst_count = info.get("numberOfAnalystOpinions") or 0

        if price == 0:
            return None
        if mkt_cap > 500_000_000:
            return None
        if short_pct < 8:
            return None

        upside_pct = round(((target_mean - price) / price * 100), 1) if target_mean > 0 else 0
        float_m = round(float_shares / 1e6, 1)
        mkt_cap_m = round(mkt_cap / 1e6, 1)

        score = score_stock(short_pct, float_m, upside_pct, analyst_count, mkt_cap_m)
        rating = get_star_rating(score)

        if rating is None:
            return None

        return {
            "ticker": ticker,
            "name": name,
            "price": price,
            "target_low": target_low,
            "target_mean": target_mean,
            "target_high": target_high,
            "upside_pct": upside_pct,
            "short_pct": round(short_pct, 1),
            "float_m": float_m,
            "mkt_cap_m": mkt_cap_m,
            "analyst_count": analyst_count,
            "sector": sector,
            "score": score,
            "rating": rating
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def format_message(r):
    arrow = "🟢" if r["upside_pct"] > 0 else "🔴"
    if r["target_mean"] > 0 and r["analyst_count"] > 0:
        target_line = (
            f"🎯 Target: ${r['target_low']} / ${r['target_mean']} / ${r['target_high']}\n"
            f"   _(Low / Mean / High — {r['analyst_count']} analysts)_\n"
            f"{arrow} Upside: {r['upside_pct']}%\n"
        )
    else:
        target_line = "🎯 Target: No analyst coverage\n"

    return (
        f"{'─' * 30}\n"
        f"*{r['ticker']}* — {r['name']}\n"
        f"{r['rating']}  (Score: {r['score']}/10)\n\n"
        f"💰 Price:    ${r['price']}\n"
        f"{target_line}"
        f"📉 Short:    {r['short_pct']}%\n"
        f"🔢 Float:    {r['float_m']}M shares\n"
        f"📊 Mkt Cap:  ${r['mkt_cap_m']}M\n"
        f"🏭 Sector:   {r['sector']}\n"
        f"[📈 Chart](https://finviz.com/quote.ashx?t={r['ticker']})\n"
    )

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
        send_telegram("✅ Scan complete — no qualifying setups today.")
        return

    results.sort(key=lambda x: x["score"], reverse=True)

    top = results[0]
    header = (
        f"🚀 *Moonshot Scan — Top Picks Today*\n"
        f"📅 {datetime.date.today()}\n"
        f"✅ {len(results)} qualifying stocks found\n"
        f"🏆 Top pick: *{top['ticker']}* (Score {top['score']}/10)\n"
    )
    send_telegram(header)

    for r in results[:8]:
        send_telegram(format_message(r))

    send_telegram(
        "⚠️ *Disclaimer:* This is a screener output, not financial advice.\n"
        "Always verify Shariah compliance on Zoya before investing.\n"
        "Past performance ≠ future results."
    )

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Debrief economique hebdomadaire - Monsieur Dazelle
Tourne chaque dimanche soir via GitHub Actions
Donnees gratuites : Yahoo Finance + Google News RSS
"""

import os
import requests
import yfinance as yf
import feedparser
from datetime import datetime, timedelta
import pytz

# Config
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
PARIS_TZ  = pytz.timezone("Europe/Paris")

def get_weekly_change(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        if len(hist) >= 2:
            start = hist["Close"].iloc[0]
            end   = hist["Close"].iloc[-1]
            change = ((end - start) / start) * 100
            return end, change
    except Exception as e:
        print(f"Erreur {symbol}: {e}")
    return None, None

def fmt(price, change, suffix="", decimals=0):
    if price is None:
        return "donnees indisponibles"
    arrow = "up" if change >= 0 else "down"
    sign  = "+" if change >= 0 else ""
    p = f"{price:,.{decimals}f}" if decimals else f"{price:,.0f}"
    return f"{arrow} {p}{suffix}  ({sign}{change:.1f}% cette semaine)"

def get_headlines(query, n=3):
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
        feed = feedparser.parse(url)
        return [f"  - {e.title}" for e in feed.entries[:n]]
    except Exception as e:
        print(f"Erreur news ({query}): {e}")
        return ["  - Impossible de charger les actualites"]

def get_upcoming_earnings():
    majors = {
        "LVMH": "MC.PA", "TotalEnergies": "TTE.PA", "Airbus": "AIR.PA",
        "BNP Paribas": "BNP.PA", "Sanofi": "SAN.PA", "Stellantis": "STLAM.MI",
        "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN",
        "Alphabet": "GOOGL", "NVIDIA": "NVDA", "Tesla": "TSLA", "Meta": "META",
        "JPMorgan": "JPM", "HSBC": "HSBA.L",
    }
    today = datetime.now(pytz.timezone("Europe/Paris")).date()
    next_week = today + timedelta(days=7)
    found = []
    for name, sym in majors.items():
        try:
            cal = yf.Ticker(sym).calendar
            if cal is None:
                continue
            if hasattr(cal, "to_dict"):
                cal = cal.to_dict()
            dates = cal.get("Earnings Date", [])
            if not hasattr(dates, "__iter__"):
                dates = [dates]
            for d in dates:
                try:
                    import pandas as pd
                    d_date = pd.Timestamp(d).date()
                    if today <= d_date <= next_week:
                        found.append(f"  - {name} : resultats le {d_date.strftime('%A %d/%m')}")
                except Exception:
                    pass
        except Exception:
            pass
    return found if found else None

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk})
        if not r.json().get("ok"):
            print(f"Erreur Telegram: {r.text}")
            return False
    return True

def main():
    now = datetime.now(PARIS_TZ)
    date_str = now.strftime("%d/%m/%Y")

    print("Recuperation des donnees marches...")
    cac_p,    cac_c    = get_weekly_change("^FCHI")
    sp500_p,  sp500_c  = get_weekly_change("^GSPC")
    nasdaq_p, nasdaq_c = get_weekly_change("^IXIC")
    btc_p,    btc_c    = get_weekly_change("BTC-EUR")
    eurusd_p, eurusd_c = get_weekly_change("EURUSD=X")

    print("Recuperation des actualites...")
    news_cac    = get_headlines("CAC 40 bourse actions france semaine")
    news_world  = get_headlines("BCE Fed banque centrale taux directeurs")
    news_btc    = get_headlines("bitcoin crypto actualite semaine")
    news_macro  = get_headlines("inflation emploi PIB economie semaine prochaine")

    print("Recuperation du calendrier economique...")
    earnings = get_upcoming_earnings()
    news_agenda_macro  = get_headlines("agenda economique indicateurs CPI inflation Fed BCE semaine prochaine", 3)
    news_agenda_result = get_headlines("resultats trimestriels publication entreprises attendus semaine prochaine", 3)

    if eurusd_p and eurusd_p > 1.10:
        eurusd_comment = "(euro fort -> tes ETF monde valent un peu moins en EUR)"
    elif eurusd_p:
        eurusd_comment = "(euro faible -> tes ETF monde valent un peu plus en EUR)"
    else:
        eurusd_comment = ""

    earnings_str = chr(10).join(earnings) if earnings else "  - Pas de resultats majeurs identifies"

    message = (
        f"Bonsoir Monsieur Dazelle - Debrief eco du {date_str}\n\n"
        f"BILAN DE LA SEMAINE\n"
        f"CAC 40 : {fmt(cac_p, cac_c, ' pts')}\n"
        f"S&P 500 : {fmt(sp500_p, sp500_c)}\n"
        f"Nasdaq  : {fmt(nasdaq_p, nasdaq_c)}\n"
        f"EUR/USD : {fmt(eurusd_p, eurusd_c, '', 4)} {eurusd_comment}\n"
        f"Bitcoin : {fmt(btc_p, btc_c, ' EUR')}\n\n"
        f"ACTU DE LA SEMAINE\n"
        f"Marches francais :\n" + chr(10).join(news_cac) + "\n\n"
        f"Banques centrales :\n" + chr(10).join(news_world) + "\n\n"
        f"Economie mondiale :\n" + chr(10).join(news_macro) + "\n\n"
        f"Crypto :\n" + chr(10).join(news_btc) + "\n\n"
        f"A SURVEILLER CETTE SEMAINE\n"
        f"Resultats d'entreprises attendus :\n{earnings_str}\n"
        f"(sources presse) :\n" + chr(10).join(news_agenda_result) + "\n\n"
        f"Donnees macro & banques centrales :\n" + chr(10).join(news_agenda_macro) + "\n\n"
        f"A RETENIR\n"
        f"Les marches bougent surtout quand sortent les chiffres de l'inflation (CPI) et les decisions de taux de la BCE ou de la Fed. Si tu vois ces mots dans l'actu cette semaine, surveille tes investissements de pres.\n\n"
        f"Bonne semaine !"
    )

    print("Envoi Telegram...")
    if send(message):
        print("Debrief envoye !")
    else:
        print("Erreur lors de l'envoi Telegram")

if __name__ == "__main__":
    main()

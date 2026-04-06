#!/usr/bin/env python3
"""
Débrief économique hebdomadaire — Monsieur Dazelle
Tourne chaque dimanche soir via GitHub Actions
Données gratuites : Yahoo Finance + CoinGecko + Google News RSS
"""

import os
import requests
import yfinance as yf
import feedparser
from datetime import datetime
import pytz

# ─── Config (depuis les secrets GitHub) ───────────────────────────────────────
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
PARIS_TZ  = pytz.timezone("Europe/Paris")

# ─── Récupération des prix ─────────────────────────────────────────────────────
def get_weekly_change(symbol):
    """Retourne (prix_actuel, variation_%_sur_5_jours)"""
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
    """Formate un prix + variation pour Telegram"""
    if price is None:
        return "données indisponibles"
    arrow = "up" if change >= 0 else "down"
    sign  = "+" if change >= 0 else ""
    p = f"{price:,.{decimals}f}" if decimals else f"{price:,.0f}"
    return f"{p}{suffix}  ({sign}{change:.1f}% cette semaine)"

# ─── Récupération des news (Google News RSS, sans clé API) ────────────────────
def get_headlines(query, n=3):
    """Retourne une liste de titres depuis Google News"""
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"
        feed = feedparser.parse(url)
        return [f"  - {e.title}" for e in feed.entries[:n]]
    except Exception as e:
        print(f"Erreur news ({query}): {e}")
        return ["  - Impossible de charger les actualités"]

# ─── Envoi Telegram ────────────────────────────────────────────────────────────
def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk})
        if not r.json().get("ok"):
            print(f"Erreur Telegram: {r.text}")
            return False
    return True

# ─── Programme principal ───────────────────────────────────────────────────────
def main():
    now = datetime.now(PARIS_TZ)
    date_str = now.strftime("%d/%m/%Y")

    print("Récupération des données marchés...")
    cac_p,    cac_c    = get_weekly_change("^FCHI")
    sp500_p,  sp500_c  = get_weekly_change("^GSPC")
    nasdaq_p, nasdaq_c = get_weekly_change("^IXIC")
    btc_p,    btc_c    = get_weekly_change("BTC-EUR")
    eurusd_p, eurusd_c = get_weekly_change("EURUSD=X")

    print("Récupération des actualités...")
    news_cac   = get_headlines("CAC 40 bourse actions france semaine")
    news_world = get_headlines("BCE Fed banque centrale taux directeurs")
    news_btc   = get_headlines("bitcoin crypto actualite semaine")
    news_macro = get_headlines("inflation emploi economie semaine")

    if eurusd_p and eurusd_p > 1.10:
        eurusd_comment = "(euro fort -> tes ETF monde valent un peu moins en euros)"
    elif eurusd_p:
        eurusd_comment = "(euro faible -> tes ETF monde valent un peu plus en euros)"
    else:
        eurusd_comment = ""

    up = lambda c: "+" if c and c >= 0 else ""
    arrow = lambda c: "En hausse" if c and c >= 0 else "En baisse"

    message = f"""Bonsoir Monsieur Dazelle - Debrief eco du {date_str}

BILAN DE LA SEMAINE ECOULEE

CAC 40 (tes actions francaises):
  {fmt(cac_p, cac_c, " pts")} {arrow(cac_c)} cette semaine

Marches americains (S&P 500 / Nasdaq):
  S&P 500 : {fmt(sp500_p, sp500_c)}
  Nasdaq  : {fmt(nasdaq_p, nasdaq_c)}

Euro / Dollar:
  {fmt(eurusd_p, eurusd_c, "", 4)} {eurusd_comment}

Bitcoin:
  {fmt(btc_p, btc_c, " EUR")} {arrow(btc_c)} cette semaine

ACTUALITES DE LA SEMAINE

Marches francais (CAC 40):
{chr(10).join(news_cac)}

Banques centrales (BCE / Fed):
(La BCE = banque centrale europeenne, la Fed = banque centrale americaine.
Leurs decisions sur les taux d'interet font bouger tous les marches.)
{chr(10).join(news_world)}

Economie mondiale:
{chr(10).join(news_macro)}

Bitcoin / Crypto:
{chr(10).join(news_btc)}

A RETENIR CETTE SEMAINE
Les marches bougent surtout quand sortent les chiffres d'inflation (CPI)
et les decisions de taux de la BCE ou de la Fed.
Si tu vois ces mots dans l'actu, surveille tes investissements de pres.

Bonne semaine !"""

    print("Envoi Telegram...")
    if send(message):
        print("Debrief envoye avec succes!")
    else:
        print("Erreur lors de l envoi Telegram")

if __name__ == "__main__":
    main()

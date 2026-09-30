import ccxt
import pandas as pd
import ta
import requests
import time
import threading
import os
from flask import Flask

# --- APNI VERIFIED DETAILS ---
BOT_TOKEN = "5356164098:AAEjSvKdZXAwMyS7xcFzakiqgUqwUZVcKdI"
CHAT_ID = "853263656"

app = Flask(__name__)

@app.route('/')
def home():
    return "Scanner is running active 24/7!"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

# Binance Futures Exchange Connection
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

def scan():
    try:
        markets = exchange.load_markets()
        symbols = [s for s in markets if '/USDT' in s and markets[s]['swap']]
        
        print(f"Scanning {len(symbols)} perpetual pairs on 15m timeframe...")
        
        for symbol in symbols:
            try:
                # 15m timeframe ki candles
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                
                # Indicators Calculation
                df['rsi'] = ta.momentum.rsi(df['close'], window=14)
                df['rsi_smooth'] = ta.trend.sma_indicator(df['rsi'], window=14)
                df['ema_high'] = ta.trend.ema_indicator(df['high'], window=30)
                df['ema_low'] = ta.trend.ema_indicator(df['low'], window=30)
                
                last = df.iloc[-1]
                prev = df.iloc[-5:] # Last 5 candles scan
                
                # 1. SHORT Scenario Logic
                if any(prev['rsi_smooth'] > 70) and any(prev['high'] > prev['ema_high']) and last['close'] < last['ema_low']:
                    msg = f"🔻 SHORT ALERT (15M): {symbol}\nPrice: {last['close']}"
                    send_telegram(msg)
                    print(msg)
                    
                # 2. LONG Scenario Logic
                if any(prev['rsi_smooth'] < 30) and any(prev['low'] < prev['ema_low']) and last['close'] > last['ema_high']:
                    msg = f"🟢 LONG ALERT (15M): {symbol}\nPrice: {last['close']}"
                    send_telegram(msg)
                    print(msg)
                    
                time.sleep(0.1) # Binance API rate limit protection
            except Exception as e:
                continue
    except Exception as e:
        print("Scan loop error:", e)

def run_scanner():
    send_telegram("🚀 15M Trading System Scanner Started Successfully!")
    while True:
        scan()
        time.sleep(180) # Har 3 minute me scan karega

if __name__ == "__main__":
    # Background Thread for Scanner
    t = threading.Thread(target=run_scanner)
    t.daemon = True
    t.start()
    
    # Dynamic Port assignment for Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

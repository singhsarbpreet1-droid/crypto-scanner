import ccxt
import pandas as pd
import ta
import requests
import time
import threading
import os
from flask import Flask

# --- TELEGRAM DETAILS ---
BOT_TOKEN = "5356164098:AAEjSvKdZXAwMyS7xcFzakiqgUqwUZVcKdI"
CHAT_ID = "853263656"

app = Flask(__name__)

@app.route('/')
def home():
    return "1:5 Risk-Reward Fib Scanner Active 24/7!"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

# Binance Futures Connection
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# Exact 4 Symbols on Binance Futures
TARGET_SYMBOLS = ['ETHUSDT', 'CLUSDT', 'XAGUSDT', 'XAUUSDT']

def calculate_fibonacci(df):
    """
    RSI > 70 setup, Swing Low below 30 EMA Low, Close above 30 EMA High,
    and Fib 1.0 to 1.618 Alert Trigger Logic.
    """
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['ema_high'] = ta.trend.ema_indicator(df['high'], window=30)
    df['ema_low'] = ta.trend.ema_indicator(df['low'], window=30)

    # 1. RSI > 70 condition check
    rsi_overbought = df[df['rsi'] > 70]
    if rsi_overbought.empty:
        return None

    last_rsi_idx = rsi_overbought.index[-1]
    df_after_rsi = df.loc[last_rsi_idx:]

    if len(df_after_rsi) < 3:
        return None

    # Swing High
    swing_high = df_after_rsi['high'].max()
    swing_high_idx = df_after_rsi['high'].idxmax()

    df_after_high = df.loc[swing_high_idx:]

    # Swing Low below 30 EMA Low
    ema_low_breaks = df_after_high[df_after_high['low'] < df_after_high['ema_low']]
    if ema_low_breaks.empty:
        return None

    swing_low = df_after_high['low'].min()
    swing_low_idx = df_after_high['low'].idxmin()

    # Close above 30 EMA High check
    df_after_low = df.loc[swing_low_idx:]
    close_above_ema = df_after_low[df_after_low['close'] > df_after_low['ema_high']]
    if close_above_ema.empty:
        return None

    # Fibonacci Calculation (Swing High to Swing Low)
    diff = swing_high - swing_low
    fib_1_0 = swing_high
    fib_1_618 = swing_high + (0.618 * diff)

    current_price = df.iloc[-1]['close']

    # Alert condition: Price in 1.0 to 1.618 zone
    if fib_1_0 <= current_price <= fib_1_618:
        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'fib_1_0': fib_1_0,
            'fib_1_618': fib_1_618,
            'current_price': current_price
        }

    return None

def scan():
    print("Scanning selected 4 pairs for 1:5 Fib setup...")
    for symbol in TARGET_SYMBOLS:
        try:
            # 15m timeframe candles
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            if not bars:
                continue
                
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            
            result = calculate_fibonacci(df)
            if result:
                msg = (
                    f"🔥 HIGH RR SETUP ALERT (1:5 Target Zone)! 🔥\n\n"
                    f"📌 Pair: {symbol}\n"
                    f"💰 Current Price: {result['current_price']}\n\n"
                    f"📈 Swing High: {result['swing_high']:.2f}\n"
                    f"📉 Swing Low: {result['swing_low']:.2f}\n\n"
                    f"🎯 Fib 1.0 Level: {result['fib_1_0']:.2f}\n"
                    f"🚀 Fib 1.618 Level: {result['fib_1_618']:.2f}\n\n"
                    f"⚡ Status: Price is currently inside 1.0 - 1.618 Breakout Zone!"
                )
                send_telegram(msg)
                print(f"Alert sent for {symbol}")
                
            time.sleep(0.2)
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

def run_scanner():
    send_telegram("🚀 1:5 FIBONACCI STRATEGY SCANNER STARTED!")
    while True:
        scan()
        time.sleep(120)  # Every 2 minutes scan

if __name__ == "__main__":
    t = threading.Thread(target=run_scanner)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

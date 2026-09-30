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
    return "Fibonacci Strategy Scanner is Active 24/7!"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

# Binance Futures Connection
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# AAPKE 4 SELECTED PAIRS
TARGET_SYMBOLS = ['ETH/USDT', 'CL/USDT', 'XAG/USDT', 'XAU/USDT']

def calculate_fibonacci(df):
    """
    RSI > 70 condition check, Swing High and Swing Low calculation,
    and Fib 1.0 to 1.618 Alert Trigger Logic.
    """
    # Indicators
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['ema_high'] = ta.trend.ema_indicator(df['high'], window=30)
    df['ema_low'] = ta.trend.ema_indicator(df['low'], window=30)

    # 1. Lookback period me check karein ki kya RSI 70 ke upar gaya tha
    rsi_overbought_idx = df[df['rsi'] > 70].index
    if rsi_overbought_idx.empty:
        return None

    last_rsi_idx = rsi_overbought_idx[-1]
    
    # RSI > 70 hone ke baad hi aage ka setup trace hoga
    df_after_rsi = df.loc[last_rsi_idx:]
    if len(df_after_rsi) < 5:
        return None

    # Swing High (RSI > 70 zone ke paas highest price)
    swing_high = df_after_rsi['high'].max()
    swing_high_idx = df_after_rsi['high'].idxmax()

    # Swing Low (Swing High ke baad aur 30 EMA Low ke niche ka lowest price)
    df_after_high = df.loc[swing_high_idx:]
    ema_low_breaks = df_after_high[df_after_high['low'] < df_after_high['ema_low']]
    
    if ema_low_breaks.empty:
        return None

    swing_low = df_after_high['low'].min()
    swing_low_idx = df_after_high['low'].idxmin()

    # 30 EMA High ke upar candle close hone ka check (Swing Low ke baad)
    df_after_low = df.loc[swing_low_idx:]
    close_above_ema_high = df_after_low[df_after_low['close'] > df_after_low['ema_high']]

    if close_above_ema_high.empty:
        return None

    # Fibonacci Retracement Levels (Swing High to Swing Low)
    diff = swing_high - swing_low
    fib_1_0 = swing_high
    fib_1_618 = swing_high + (0.618 * diff)

    current_price = df.iloc[-1]['close']

    # Check if price is in 1.0 to 1.618 zone
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
    print("Scanning selected 4 pairs for Fibonacci setup...")
    for symbol in TARGET_SYMBOLS:
        try:
            # 15m timeframe candles fetch
            bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            if not bars:
                continue
                
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            
            result = calculate_fibonacci(df)
            if result:
                msg = (
                    f"🎯 FIBONACCI BREAKOUT ALERT!\n\n"
                    f"🔹 Pair: {symbol}\n"
                    f"🔹 Current Price: {result['current_price']}\n"
                    f"🔹 Swing High: {result['swing_high']}\n"
                    f"🔹 Swing Low: {result['swing_low']}\n"
                    f"📊 Fib 1.0 Level: {result['fib_1_0']:.2f}\n"
                    f"📊 Fib 1.618 Level: {result['fib_1_618']:.2f}\n\n"
                    f"⚡ Price is currently in 1.0 - 1.618 Golden Zone!"
                )
                send_telegram(msg)
                print(f"Alert sent for {symbol}")
                
            time.sleep(0.2)
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

def run_scanner():
    send_telegram("🚀 New Fibonacci 15M Strategy Scanner Started!")
    while True:
        scan()
        time.sleep(120)  # Scan every 2 minutes

if __name__ == "__main__":
    t = threading.Thread(target=run_scanner)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

import telebot
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import threading
import os
from datetime import datetime
from groq import Groq  # Free & Fast AI

# Config
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
GROUP_CHAT_ID = "YOUR_GROUP_CHAT_ID_HERE"
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"  # ទទួលឥតគិតថ្លៃនៅ groq.com

bot = telebot.TeleBot(TELEGRAM_TOKEN)
exchange = ccxt.binance({'enableRateLimit': True})

SYMBOL = 'XAUUSD'
TIMEFRAME = '1m'
CHECK_INTERVAL = 60  # រាល់ ១ នាទី

client = Groq(api_key=GROQ_API_KEY)

def get_ai_analysis(df, current_price):
    try:
        # Prepare market summary for AI
        latest = df.iloc[-1]
        summary = f"""
Current XAUUSD 1m:
Price: {current_price:.2f}
RSI: {latest.get('rsi', 'N/A'):.1f}
MACD: {latest.get('macd', 'N/A'):.4f}
BB Position: {'Above upper' if latest['close'] > latest.get('bb_upper', 0) else 'Below lower' if latest['close'] < latest.get('bb_lower', 0) else 'Middle'}
Recent trend: {'Up' if df['close'].iloc[-5:].is_monotonic_increasing else 'Down' if df['close'].iloc[-5:].is_monotonic_decreasing else 'Sideways'}
        """
        
        prompt = f"""You are a professional scalping trader for Gold (XAUUSD). 
Analyze the data below and give a clear scalping signal (BUY/SELL/NEUTRAL) with Entry, TP1, TP2, SL.
Be strict, only give strong signals. Focus on 1-minute scalping.

Data: {summary}

Respond in JSON format:
{{
  "signal": "BUY or SELL or NEUTRAL",
  "confidence": 0-100,
  "entry": number,
  "tp1": number,
  "tp2": number,
  "sl": number,
  "reason": "short explanation"
}}
"""
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",  # Free fast model
            temperature=0.3,
            max_tokens=400
        )
        import json
        ai_response = chat_completion.choices[0].message.content
        return json.loads(ai_response)
    except:
        return None

def analyze_and_alert():
    while True:
        try:
            print(f"[{datetime.now()}] AI Analyzing {SYMBOL}...")
            
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=150)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            df['rsi'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            bb = ta.bbands(df['close'])
            df['bb_upper'] = bb['BBU_5_2.0']
            df['bb_lower'] = bb['BBL_5_2.0']
            
            current_price = df['close'].iloc[-1]
            
            # Get Deep AI Thinking
            ai_result = get_ai_analysis(df, current_price)
            
            if ai_result and ai_result.get("signal") in ["BUY", "SELL"] and ai_result.get("confidence", 0) > 65:
                signal_text = "🟢 STRONG BUY" if ai_result["signal"] == "BUY" else "🔴 STRONG SELL"
                
                response = f"""
🚨 **AI DEEP THINKING SIGNAL - {SYMBOL}**
**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Signal**: {signal_text} (Confidence: {ai_result['confidence']}%)
**Price**: {current_price:.2f}
**Entry**: ~{ai_result['entry']:.2f}
**TP1**: {ai_result['tp1']:.2f}
**TP2**: {ai_result['tp2']:.2f}
**SL**: {ai_result['sl']:.2f}
**AI Reason**: {ai_result['reason']}
⚠️ Scalping 1m • Risk only 0.5% per trade
                """
                bot.send_message(GROUP_CHAT_ID, response)
                print("✅ AI Signal sent to group!")
            else:
                print("🤔 No strong AI signal this time.")
                
        except Exception as e:
            print(f"Error: {str(e)[:100]}")
        
        time.sleep(CHECK_INTERVAL)

# Run auto thread
thread = threading.Thread(target=analyze_and_alert, daemon=True)
thread.start()

print("✅ AI Deep Thinking Scalping Bot for XAUUSD កំពុងដំណើរការ...")
bot.polling()

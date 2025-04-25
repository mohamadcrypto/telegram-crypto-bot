import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import ta
import os
import openai
from PIL import Image
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def analyze_symbol(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "❌ لا توجد بيانات تحليل كافية."

    try:
        df["ema20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
        df["ema50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
        df["ema200"] = ta.trend.EMAIndicator(df["close"], window=200).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df["close"])
        df["bb_high"] = bb.bollinger_hband()
        df["bb_low"] = bb.bollinger_lband()
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        stoch = ta.momentum.StochRSIIndicator(df["close"])
        df["stoch_k"] = stoch.stochrsi_k()
        df["stoch_d"] = stoch.stochrsi_d()

        latest = df.iloc[-1]
        analysis = []

        if latest["rsi"] < 30:
            analysis.append("🔹 RSI يشير إلى تشبع بيعي.")
        elif latest["rsi"] > 70:
            analysis.append("🔸 RSI يشير إلى تشبع شرائي.")

        if latest["macd"] > latest["macd_signal"]:
            analysis.append("✅ MACD تقاطع صعودي.")
        else:
            analysis.append("⚠️ MACD تقاطع هبوطي.")

        if latest["close"] > latest["ema200"]:
            analysis.append("📈 السعر فوق EMA200 - اتجاه عام صاعد.")
        else:
            analysis.append("📉 السعر تحت EMA200 - اتجاه عام هابط.")

        if latest["adx"] > 25:
            analysis.append("💪 ADX يشير إلى اتجاه قوي.")
        else:
            analysis.append("😐 ADX يشير إلى ضعف الاتجاه.")

        if latest["close"] < latest["bb_low"]:
            analysis.append("📉 السعر تحت Bollinger Band – ممكن ارتداد.")
        elif latest["close"] > latest["bb_high"]:
            analysis.append("📈 السعر فوق Bollinger Band – ممكن تصحيح.")

        support = df["low"][-10:].min()
        resistance = df["high"][-10:].max()
        analysis.append(f"📊 الدعم: {round(support, 4)}")
        analysis.append(f"📊 المقاومة: {round(resistance, 4)}")

        return "\n".join(analysis)

    except Exception as e:
        return f"❌ خطأ أثناء التحليل: {str(e)}"

def add_watermark_to_image(chart_path, logo_path):
    base = Image.open(chart_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((300, 300))
    base_width, base_height = base.size
    logo_width, logo_height = logo.size
    x = (base_width - logo_width) // 2
    y = (base_height - logo_height) // 2
    base.paste(logo, (x, y), logo)
    base.save(chart_path)

def plot_chart(df, symbol: str):
    df["EMA20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["EMA50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["EMA200"] = ta.trend.EMAIndicator(df["close"], window=200).ema_indicator()
    bb = ta.volatility.BollingerBands(df["close"])
    df["BB_HIGH"] = bb.bollinger_hband()
    df["BB_LOW"] = bb.bollinger_lband()

    df_plot = df[["open", "high", "low", "close", "volume"]].copy()
    df_plot.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    add_plots = [
        mpf.make_addplot(df["EMA20"], color='blue'),
        mpf.make_addplot(df["EMA50"], color='orange'),
        mpf.make_addplot(df["EMA200"], color='red'),
        mpf.make_addplot(df["BB_HIGH"], color='green'),
        mpf.make_addplot(df["BB_LOW"], color='green')
    ]

    filename = f"{symbol}_chart.png"

    fig, _ = mpf.plot(
        df_plot,
        type='candle',
        style='charles',
        title=f"{symbol} - Technical Chart",
        ylabel='Price',
        volume=True,
        addplot=add_plots,
        returnfig=True
    )
    fig.savefig(filename, dpi=100, bbox_inches='tight')
    add_watermark_to_image(filename, "logo.png")

    return filename

def generate_gpt_analysis(symbol: str, timeframe: str, technical_summary: str) -> str:
    prompt = (
        f"بناءً على البيانات الفنية التالية لعملة {symbol} على فريم {timeframe}:\n"
        f"{technical_summary}\n\n"
        "اكتب ملخصًا ذكيًا بلغة بشرية بسيطة دون إعادة ذكر اسم العملة أو الفريم، "
        "يشمل الاتجاه العام، إشارات الدخول أو الخروج المحتملة، ونصيحة عامة."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"⚠️ تعذر توليد تحليل ذكي: {e}"
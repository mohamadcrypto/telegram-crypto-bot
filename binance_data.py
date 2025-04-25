import requests
import pandas as pd

def get_klines(symbol: str, interval: str = "1h", limit: int = 100):
    """
    جلب بيانات الشموع لرمز معين من Binance Spot API
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"خطأ في جلب البيانات: {response.text}")

    data = response.json()

    # تحويل البيانات إلى DataFrame
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    # تحويل الأعمدة الرقمية إلى float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df

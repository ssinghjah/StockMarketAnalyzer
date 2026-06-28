from flask import Flask, render_template, request
import requests
import pandas as pd
import json

app = Flask(__name__)

API_KEY = "0MNUBBQN1KN39QBB"

SERIES_CONFIG = {
    "daily": {
        "function": "TIME_SERIES_DAILY",
        "key": "Time Series (Daily)",
        "label": "Daily",
        "date_fmt": "%Y-%m-%d",
        "index_name": "Date",
    },
    "weekly": {
        "function": "TIME_SERIES_WEEKLY",
        "key": "Weekly Time Series",
        "label": "Weekly",
        "date_fmt": "%Y-%m-%d",
        "index_name": "Week Ending",
    },
    "monthly": {
        "function": "TIME_SERIES_MONTHLY",
        "key": "Monthly Time Series",
        "label": "Monthly",
        "date_fmt": "%Y-%m-%d",
        "index_name": "Month Ending",
    },
    "intraday": {
        "function": "TIME_SERIES_INTRADAY",
        "key": None,  # dynamic: "Time Series ({interval})"
        "label": "Intraday",
        "date_fmt": "%Y-%m-%d %H:%M:%S",
        "index_name": "Datetime",
    },
}


def get_stock_data(symbol, series="daily", interval="5min"):
    config = SERIES_CONFIG.get(series, SERIES_CONFIG["daily"])

    url = (
        "https://www.alphavantage.co/query?"
        f"function={config['function']}"
        f"&symbol={symbol}"
        f"&outputsize=compact"
        f"&apikey={API_KEY}"
    )

    if series == "intraday":
        url += f"&interval={interval}"
        series_key = f"Time Series ({interval})"
    else:
        series_key = config["key"]

    response = requests.get(url)
    data = response.json()

    with open(f"{symbol}_response.txt", "w") as f:
        json.dump(data, f, indent=4)

    print(data)

    # Detect API-level errors (premium restriction, rate limit, invalid symbol)
    if "Information" in data:
        return None, data["Information"]
    if "Note" in data:
        return None, data["Note"]
    if "Error Message" in data:
        return None, data["Error Message"]

    if series_key not in data:
        return None, f"No data returned for '{symbol}'. Check the ticker symbol."

    df = pd.DataFrame.from_dict(
        data[series_key],
        orient="index"
    )

    df.index = pd.to_datetime(df.index)

    df["Open"]   = df["1. open"].astype(float)
    df["High"]   = df["2. high"].astype(float)
    df["Low"]    = df["3. low"].astype(float)
    df["Volume"] = df["5. volume"].astype(int)

    df = df[["Open", "High", "Low", "Volume"]]
    df = df.sort_index(ascending=False)
    df.index.name = config["index_name"]
    df.index = df.index.strftime(config["date_fmt"])
    df.columns = ["Open ($)", "High ($)", "Low ($)", "Volume (shares)"]

    return df, None


@app.route("/", methods=["GET", "POST"])
def index():

    table = None
    symbol = "AAPL"
    series = "daily"
    interval = "5min"
    error = None

    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        series = request.form.get("series", "daily")
        interval = request.form.get("interval", "5min")

    df, error = get_stock_data(symbol, series, interval)

    if df is not None:
        table = df.to_html(
            classes="stock-table",
            border=0
        )

    series_label = SERIES_CONFIG.get(series, SERIES_CONFIG["daily"])["label"]
    if series == "intraday":
        series_label = f"Intraday ({interval})"

    return render_template(
        "index.html",
        table=table,
        symbol=symbol,
        series=series,
        interval=interval,
        series_label=series_label,
        error=error,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5005,
        debug=True
    )

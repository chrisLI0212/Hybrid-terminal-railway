from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import requests

try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False

try:
    from polygon import RESTClient as PolygonClient
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False

try:
    from eodhd import APIClient as EODHDClient
    EODHD_AVAILABLE = True
except ImportError:
    EODHD_AVAILABLE = False

app = Flask(__name__, template_folder='templates')
CORS(app, resources={r"/api/*": {"origins": "*"}})

TICKER_CONFIG = {
    "primary_tickers": [
        {
            "id": "SPX",
            "label": "SPX - S&P 500 Index",
            "providers": {
                "eodhd": "SPX.INDX",
                "databento": {"symbol": "SPX", "dataset": "GLBX.MDP3", "schema": "ohlcv-1h"},
                "polygon": "I:SPX",
                "theta": "SPX"
            }
        },
        {
            "id": "SPY",
            "label": "SPY - SPDR S&P 500 ETF",
            "providers": {
                "eodhd": "SPY.US",
                "databento": {"symbol": "SPY", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"},
                "polygon": "SPY",
                "theta": "SPY"
            }
        },
        {
            "id": "QQQ",
            "label": "QQQ - Invesco QQQ Trust",
            "providers": {
                "eodhd": "QQQ.US",
                "databento": {"symbol": "NQ", "dataset": "GLBX.MDP3", "schema": "ohlcv-1h"},
                "polygon": "QQQ",
                "theta": "QQQ"
            }
        },
        {
            "id": "VIX",
            "label": "VIX - Volatility Index",
            "providers": {
                "eodhd": "VIX.INDX",
                "databento": {"symbol": "VX", "dataset": "GLBX.MDP3", "schema": "ohlcv-1h"},
                "polygon": "I:VIX",
                "theta": "VIX"
            }
        },
        {
            "id": "TLT",
            "label": "TLT - Treasury ETF",
            "providers": {
                "eodhd": "TLT.US",
                "databento": {"symbol": "TLT", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"},
                "polygon": "TLT",
                "theta": "TLT"
            }
        }
    ],
    "mag7_tickers": [
        {"id": "NVDA", "label": "NVDA - NVIDIA", "providers": {"eodhd": "NVDA.US", "databento": {"symbol": "NVDA", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "NVDA", "theta": "NVDA"}},
        {"id": "MSFT", "label": "MSFT - Microsoft", "providers": {"eodhd": "MSFT.US", "databento": {"symbol": "MSFT", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "MSFT", "theta": "MSFT"}},
        {"id": "GOOGL", "label": "GOOGL - Alphabet", "providers": {"eodhd": "GOOGL.US", "databento": {"symbol": "GOOGL", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "GOOGL", "theta": "GOOGL"}},
        {"id": "AMZN", "label": "AMZN - Amazon", "providers": {"eodhd": "AMZN.US", "databento": {"symbol": "AMZN", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "AMZN", "theta": "AMZN"}},
        {"id": "TSLA", "label": "TSLA - Tesla", "providers": {"eodhd": "TSLA.US", "databento": {"symbol": "TSLA", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "TSLA", "theta": "TSLA"}},
        {"id": "META", "label": "META - Meta", "providers": {"eodhd": "META.US", "databento": {"symbol": "META", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "META", "theta": "META"}},
        {"id": "NFLX", "label": "NFLX - Netflix", "providers": {"eodhd": "NFLX.US", "databento": {"symbol": "NFLX", "dataset": "XNAS.ITCH", "schema": "ohlcv-1h"}, "polygon": "NFLX", "theta": "NFLX"}}
    ],
    "databento_datasets": [
        {"id": "GLBX.MDP3", "label": "CME Globex", "description": "SPX, NQ, ES, VX"},
        {"id": "XNAS.ITCH", "label": "Nasdaq", "description": "Stocks/ETFs"},
        {"id": "OPRA", "label": "Options", "description": "Options data"}
    ],
    "databento_schemas": [
        {"id": "ohlcv-1h", "label": "1-Hour OHLCV"},
        {"id": "ohlcv-1d", "label": "1-Day OHLCV"},
        {"id": "trades", "label": "Tick Trades"},
        {"id": "tbbo", "label": "Top of Book"}
    ],
    "eodhd_options_tickers": [
        {"id": "SPY.US", "label": "SPY Options"},
        {"id": "QQQ.US", "label": "QQQ Options"},
        {"id": "TLT.US", "label": "TLT Options"}
    ],
    "theta_options_types": [
        {"id": "occ", "label": "OCC Options - Historical Greeks"},
        {"id": "quote", "label": "Options Quote - Real-time Bid/Ask"},
        {"id": "trade", "label": "Options Trade - Tick Data"}
    ]
}

stored_settings = {"api_keys": {}}
databento_client = None
polygon_client = None
eodhd_client = None
theta_token = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config/tickers', methods=['GET'])
def get_tickers():
    return jsonify({"success": True, "primary_tickers": TICKER_CONFIG["primary_tickers"], "mag7_tickers": TICKER_CONFIG["mag7_tickers"]}), 200

@app.route('/api/config/databento', methods=['GET'])
def get_databento_config():
    return jsonify({"success": True, "datasets": TICKER_CONFIG["databento_datasets"], "schemas": TICKER_CONFIG["databento_schemas"]}), 200

@app.route('/api/config/options-tickers', methods=['GET'])
def get_options_tickers():
    return jsonify({"success": True, "options_tickers": TICKER_CONFIG["eodhd_options_tickers"]}), 200

@app.route('/api/config/theta', methods=['GET'])
def get_theta_config():
    return jsonify({"success": True, "options_types": TICKER_CONFIG["theta_options_types"]}), 200

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"success": True, "status": "ok", "timestamp": datetime.now().isoformat(), "providers": {"databento": DATABENTO_AVAILABLE, "polygon": POLYGON_AVAILABLE, "eodhd": EODHD_AVAILABLE, "theta": theta_token is not None}}), 200

@app.route('/api/keys', methods=['POST'])
def add_api_key():
    global databento_client, polygon_client, eodhd_client, theta_token
    try:
        data = request.get_json()
        name = data.get("name", "").lower()
        key = data.get("key")
        if not name or not key:
            return jsonify({"success": False, "error": "Name and key required"}), 400
        stored_settings["api_keys"][name] = key
        if name == "databento" and DATABENTO_AVAILABLE:
            databento_client = db.Historical(key)
        elif name == "polygon" and POLYGON_AVAILABLE:
            polygon_client = PolygonClient(key)
        elif name == "eodhd" and EODHD_AVAILABLE:
            eodhd_client = EODHDClient(key)
        elif name == "theta":
            theta_token = key
        return jsonify({"success": True, "message": f"API key '{name}' saved", "keys": list(stored_settings["api_keys"].keys())}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/keys', methods=['GET'])
def get_api_keys():
    return jsonify({"success": True, "keys": {k: "***" + v[-4:] if len(v) > 4 else "***" for k, v in stored_settings.get("api_keys", {}).items()}}), 200

@app.route('/api/data/eodhd/historical', methods=['POST'])
def fetch_eodhd_historical():
    try:
        data = request.get_json()
        ticker_id = data.get("ticker")
        start_date = data.get("start", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date = data.get("end", datetime.now().strftime("%Y-%m-%d"))
        ticker = None
        for category in [TICKER_CONFIG["primary_tickers"], TICKER_CONFIG["mag7_tickers"]]:
            for t in category:
                if t["id"] == ticker_id:
                    ticker = t["providers"]["eodhd"]
                    break
        if not ticker:
            return jsonify({"success": False, "error": f"Ticker {ticker_id} not found"}), 400
        api_key = stored_settings["api_keys"].get("eodhd")
        if not api_key:
            return jsonify({"success": False, "error": "EODHD API key not set"}), 400
        url = f"https://eodhd.com/api/eod/{ticker}"
        params = {"from": start_date, "to": end_date, "api_token": api_key, "fmt": "json"}
        response = requests.get(url, params=params)
        result = response.json()
        return jsonify({"success": True, "provider": "eodhd", "ticker": ticker_id, "data": result, "count": len(result) if isinstance(result, list) else 0}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/data/eodhd/options', methods=['POST'])
def fetch_eodhd_options():
    try:
        data = request.get_json()
        ticker_id = data.get("ticker")
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        api_key = stored_settings["api_keys"].get("eodhd")
        if not api_key:
            return jsonify({"success": False, "error": "EODHD API key not set"}), 400
        url = f"https://eodhd.com/api/options/{ticker_id}"
        params = {"from": date, "to": date, "api_token": api_key}
        response = requests.get(url, params=params)
        result = response.json()
        return jsonify({"success": True, "provider": "eodhd", "ticker": ticker_id, "date": date, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/data/theta/options', methods=['POST'])
def fetch_theta_options():
    try:
        global theta_token
        data = request.get_json()
        ticker_id = data.get("ticker")
        option_type = data.get("option_type", "occ")
        start_date = data.get("start", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date = data.get("end", datetime.now().strftime("%Y-%m-%d"))
        
        ticker = None
        for category in [TICKER_CONFIG["primary_tickers"], TICKER_CONFIG["mag7_tickers"]]:
            for t in category:
                if t["id"] == ticker_id:
                    ticker = t["providers"]["theta"]
                    break
        
        if not ticker:
            return jsonify({"success": False, "error": f"Ticker {ticker_id} not found"}), 400
        
        api_key = stored_settings["api_keys"].get("theta")
        if not api_key:
            return jsonify({"success": False, "error": "Theta Data API key not set"}), 400
        
        base_url = "https://api.thetadata.us/api/v3/historical/option"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        if option_type == "occ":
            params = {"symbol": ticker, "start_date": start_date, "end_date": end_date, "output": "json"}
            url = f"{base_url}/occ"
        elif option_type == "quote":
            params = {"symbol": ticker, "output": "json"}
            url = f"{base_url}/quote"
        elif option_type == "trade":
            params = {"symbol": ticker, "start_date": start_date, "end_date": end_date, "output": "json"}
            url = f"{base_url}/trade"
        else:
            return jsonify({"success": False, "error": f"Invalid option type: {option_type}"}), 400
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"Theta Data API error: {response.text}"}), 400
        
        result = response.json()
        
        if isinstance(result, list):
            data_list = result
            count = len(data_list)
        elif isinstance(result, dict) and "data" in result:
            data_list = result.get("data", [])
            count = len(data_list)
        else:
            data_list = [result]
            count = 1
        
        return jsonify({
            "success": True, 
            "provider": "theta",
            "ticker": ticker_id,
            "option_type": option_type,
            "start_date": start_date,
            "end_date": end_date,
            "data": data_list,
            "count": count
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/data/databento/historical', methods=['POST'])
def fetch_databento_historical():
    try:
        if not databento_client:
            return jsonify({"success": False, "error": "Databento client not initialized"}), 400
        data = request.get_json()
        ticker_id = data.get("ticker")
        dataset = data.get("dataset", "GLBX.MDP3")
        schema = data.get("schema", "ohlcv-1h")
        start = data.get("start", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        end = data.get("end", datetime.now().strftime("%Y-%m-%d"))
        symbol = None
        for category in [TICKER_CONFIG["primary_tickers"], TICKER_CONFIG["mag7_tickers"]]:
            for t in category:
                if t["id"] == ticker_id:
                    db_config = t["providers"]["databento"]
                    symbol = db_config["symbol"]
                    break
        if not symbol:
            return jsonify({"success": False, "error": f"Ticker {ticker_id} not found"}), 400
        result = databento_client.timeseries.get_range(dataset=dataset, symbols=symbol, schema=schema, start=start, end=end)
        data_list = []
        for row in result:
            data_list.append({"timestamp": str(row.ts_event), "open": float(getattr(row, 'open', None) or 0), "high": float(getattr(row, 'high', None) or 0), "low": float(getattr(row, 'low', None) or 0), "close": float(getattr(row, 'close', None) or 0), "volume": float(getattr(row, 'volume', None) or 0)})
        return jsonify({"success": True, "provider": "databento", "ticker": ticker_id, "dataset": dataset, "schema": schema, "data": data_list, "count": len(data_list)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/data/polygon/historical', methods=['POST'])
def fetch_polygon_historical():
    try:
        if not polygon_client:
            return jsonify({"success": False, "error": "Polygon client not initialized"}), 400
        data = request.get_json()
        ticker_id = data.get("ticker")
        timespan = data.get("timespan", "hour")
        multiplier = data.get("multiplier", 1)
        start_date = data.get("start", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        end_date = data.get("end", datetime.now().strftime("%Y-%m-%d"))
        ticker = None
        for category in [TICKER_CONFIG["primary_tickers"], TICKER_CONFIG["mag7_tickers"]]:
            for t in category:
                if t["id"] == ticker_id:
                    ticker = t["providers"]["polygon"]
                    break
        if not ticker:
            return jsonify({"success": False, "error": f"Ticker {ticker_id} not found"}), 400
        aggs = polygon_client.get_aggs(ticker=ticker, multiplier=multiplier, timespan=timespan, from_=start_date, to=end_date)
        data_list = []
        for agg in aggs:
            data_list.append({"timestamp": agg.timestamp, "open": agg.open, "high": agg.high, "low": agg.low, "close": agg.close, "volume": agg.volume, "vwap": getattr(agg, 'vwap', None)})
        return jsonify({"success": True, "provider": "polygon", "ticker": ticker_id, "timespan": timespan, "data": data_list, "count": len(data_list)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

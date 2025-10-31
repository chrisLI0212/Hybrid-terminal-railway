from flask import Flask, request, jsonify, send_file
import requests
import os
import io
import csv
import json

app = Flask(__name__)

# Load API keys from environment variables or default
API_KEYS = {
    'eodhd': os.getenv('EODHD_API_KEY', ''),
    'databento': os.getenv('DATABENTO_API_KEY', ''),
    'polygon': os.getenv('POLYGON_API_KEY', ''),
    'theta': os.getenv('THETA_API_KEY', '')
}

# Ticker mapping for different providers
def map_ticker(provider, ticker):
    # Define your default mappings here
    mappings = {
        'eodhd': {
            'SPX': 'SPX.INDX',
            'SPY': 'SPY.US',
            'QQQ': 'QQQ.US',
            'VIX': 'VIX.INDX',
            'TLT': 'TLT.US'
        },
        'polygon': {
            'SPX': 'I:SPX',
            'SPY': 'SPY',
            'QQQ': 'QQQ',
            'VIX': 'VIX',
            'TLT': 'TLT'
        },
        'databento': {
            'SPX': {'symbol': 'SPX', 'dataset': 'XNAS.ITCH', 'schema': 'ohlcv-1h'},
            'SPY': {'symbol': 'SPY', 'dataset': 'XNAS.ITCH', 'schema': 'ohlcv-1h'},
            'QQQ': {'symbol': 'QQQ', 'dataset': 'XNAS.ITCH', 'schema': 'ohlcv-1h'},
            'VIX': {'symbol': 'VIX', 'dataset': 'XNAS.ITCH', 'schema': 'ohlcv-1h'},
            'TLT': {'symbol': 'TLT', 'dataset': 'XNAS.ITCH', 'schema': 'ohlcv-1h'}
        },
        'theta': {
            'SPX': 'SPX',
            'SPY': 'SPY',
            'QQQ': 'QQQ',
            'VIX': 'VIX',
            'TLT': 'TLT'
        }
    }
    return mappings.get(provider, {}).get(ticker, ticker)

# Route to set and store API keys via POST (optional)
@app.route('/api/set_keys', methods=['POST'])
def set_keys():
    data = request.json
    for k in ['eodhd', 'databento', 'polygon', 'theta']:
        if k in data:
            os.environ[k.upper()+'_API_KEY'] = data[k]
            API_KEYS[k] = data[k]
    return jsonify({'status': 'success', 'message': 'API keys updated'})

# Helper: get headers for requests
def get_headers(provider):
    if provider == 'theta':
        return {'Authorization': f'Bearer {API_KEYS["theta"]}'}
    # For other providers, add headers if needed
    return {}

# EODHD data fetch endpoint
@app.route('/api/eodhd', methods=['POST'])
def fetch_eodhd():
    data = request.json
    ticker = data.get('ticker')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    mapped_ticker = map_ticker('eodhd', ticker)
    url = f'https://eodhd.com/api/eod/{mapped_ticker}/history'
    params = {
        'from': start_date,
        'to': end_date,
        'api_token': API_KEYS['eodhd']
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data_json = resp.json()
        return jsonify({'success': True, 'provider': 'eodhd', 'ticker': ticker, 'data': data_json.get('data', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Databento OHLCV fetch endpoint
@app.route('/api/databento', methods=['POST'])
def fetch_databento():
    data = request.json
    symbol = data.get('ticker')
    dataset = data.get('dataset', 'XNAS.ITCH')
    schema = data.get('schema', 'ohlcv-1h')
    from_date = data.get('start_date')
    to_date = data.get('end_date')

    url = '

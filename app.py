from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

EODHD_BASE = "https://eodhistoricaldata.com/api/eod/"
DATABENTO_BASE = "https://hist.databento.com/v0/timeseries.get_range"
POLYGON_BASE = "https://api.polygon.io/v2/aggs/ticker/"

TICKER_MAP = {
    'SPX': {'eodhd': 'SPX.INDX', 'databento': 'SPXW', 'polygon': 'I:SPX'},
    'SPY': {'eodhd': 'SPY.US', 'databento': 'SPY', 'polygon': 'SPY'},
    'VIX': {'eodhd': '^VIX', 'databento': 'VIX', 'polygon': 'I:VIX'},
    'AAPL': {'eodhd': 'AAPL.US', 'polygon': 'AAPL'},
    'TSLA': {'eodhd': 'TSLA.US', 'polygon': 'TSLA'},
    'AMZN': {'eodhd': 'AMZN.US', 'polygon': 'AMZN'},
}

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/test/<provider>', methods=['POST'])
def test_api(provider):
    try:
        api_key = request.json.get('apiKey')
        if not api_key:
            return jsonify({'success': False, 'error': 'No API key provided'}), 400
        
        if provider == 'eodhd':
            url = f"{EODHD_BASE}SPX?api_token={api_key}&fmt=json&limit=1"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return jsonify({'success': True, 'records': 1})
            return jsonify({'success': False, 'error': f'HTTP {resp.status_code}'})
        
        elif provider == 'databento':
            headers = {'Authorization': f'Bearer {api_key}'}
            params = {
                'dataset': 'OPRA',
                'symbols': 'SPXW',
                'start': '2025-10-20T00:00Z',
                'end': '2025-10-21T23:59Z'
            }
            resp = requests.get(DATABENTO_BASE, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('records', [])
                return jsonify({'success': True, 'records': len(data)})
            return jsonify({'success': False, 'error': f'HTTP {resp.status_code}'})
        
        elif provider == 'polygon':
            url = f"{POLYGON_BASE}SPX/range/1/day/2025-10-20/2025-10-21"
            params = {'apiKey': api_key}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get('results', [])
                return jsonify({'success': True, 'records': len(data)})
            return jsonify({'success': False, 'error': f'HTTP {resp.status_code}'})
        
        return jsonify({'success': False, 'error': 'Unknown provider'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/fetch', methods=['POST'])
def fetch_data():
    try:
        data = request.json
        tickers = data.get('tickers', [])
        from_date = data.get('from', '')
        to_date = data.get('to', '')
        frequency = data.get('frequency', '1d')
        tier = data.get('tier', 3)
        
        eodhd_key = data.get('eodhd_key', '')
        databento_key = data.get('databento_key', '')
        polygon_key = data.get('polygon_key', '')
        
        all_data = []
        
        for ticker in tickers:
            mapping = TICKER_MAP.get(ticker, {})
            
            # EODHD
            if mapping.get('eodhd') and eodhd_key:
                try:
                    period = 'd' if frequency == '1d' else 'h' if frequency == '1h' else '1m'
                    url = f"{EODHD_BASE}{mapping['eodhd']}"
                    params = {
                        'from': from_date,
                        'to': to_date,
                        'period': period,
                        'api_token': eodhd_key,
                        'fmt': 'json'
                    }
                    resp = requests.get(url, params=params, timeout=15)
                    if resp.status_code == 200:
                        records = resp.json()
                        for r in records:
                            r['source'] = 'EODHD'
                            r['ticker'] = ticker
                        all_data.extend(records)
                except Exception as e:
                    print(f"EODHD error: {e}")
            
            # Databento
            if mapping.get('databento') and databento_key:
                try:
                    headers = {'Authorization': f'Bearer {databento_key}'}
                    params = {
                        'dataset': 'OPRA',
                        'symbols': mapping['databento'],
                        'start': f'{from_date}T00:00Z',
                        'end': f'{to_date}T23:59Z',
                        'timespan': frequency
                    }
                    resp = requests.get(DATABENTO_BASE, params=params, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        records = resp.json().get('records', [])
                        for r in records:
                            r['source'] = 'Databento'
                            r['ticker'] = ticker
                        all_data.extend(records)
                except Exception as e:
                    print(f"Databento error: {e}")
            
            # Polygon
            if mapping.get('polygon') and polygon_key:
                try:
                    timespan = 'day' if frequency == '1d' else 'hour' if frequency == '1h' else 'minute'
                    url = f"{POLYGON_BASE}{mapping['polygon']}/range/1/{timespan}/{from_date}/{to_date}"
                    params = {'apiKey': polygon_key, 'sort': 'asc', 'limit': 50000}
                    resp = requests.get(url, params=params, timeout=15)
                    if resp.status_code == 200:
                        records = resp.json().get('results', [])
                        for r in records:
                            r['source'] = 'Polygon'
                            r['ticker'] = ticker
                        all_data.extend(records)
                except Exception as e:
                    print(f"Polygon error: {e}")
        
        return jsonify({'success': True, 'data': all_data, 'count': len(all_data)})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)

# ============================================================================
# CORS CONFIGURATION - ENABLE FOR S3 FRONTEND ACCESS
# ============================================================================
CORS(app, 
     resources={
         r"/api/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": False,
             "max_age": 3600
         }
     },
     expose_headers=['Content-Type', 'X-Total-Count'])

app.config['JSON_SORT_KEYS'] = False

# ============================================================================
# IN-MEMORY STORAGE
# ============================================================================
stored_settings = {
    "api_base_url": "",
    "api_keys": {},
    "tickers": []
}

stored_data = {
    "tickers": {},
    "last_update": None
}

# ============================================================================
# CORS PREFLIGHT HANDLER
# ============================================================================

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({"success": True})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        return response

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "success": True,
        "status": "ok",
        "message": "Hybrid Terminal Backend is Running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "backend": "Railway Production"
    }), 200

@app.route('/api/test', methods=['GET', 'POST', 'OPTIONS'])
def test():
    """Test connection endpoint"""
    if request.method == "OPTIONS":
        return "", 200
    
    return jsonify({
        "success": True,
        "message": "Backend Connection Test Successful",
        "data": "Hybrid Terminal API is Working!",
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify({
        "success": True,
        "settings": {
            "api_base_url": stored_settings.get("api_base_url", ""),
            "api_keys": stored_settings.get("api_keys", {}),
            "tickers": stored_settings.get("tickers", [])
        }
    }), 200

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.get_json()
        
        if "api_base_url" in data:
            stored_settings["api_base_url"] = data["api_base_url"]
        
        if "api_keys" in data:
            stored_settings["api_keys"] = data["api_keys"]
        
        if "tickers" in data:
            stored_settings["tickers"] = data["tickers"]
        
        return jsonify({
            "success": True,
            "message": "Settings updated successfully",
            "settings": stored_settings
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/settings/save', methods=['POST'])
def save_settings():
    """Save settings (alias for update)"""
    return update_settings()

# ============================================================================
# API KEY ENDPOINTS
# ============================================================================

@app.route('/api/keys', methods=['GET'])
def get_api_keys():
    """Get stored API keys"""
    return jsonify({
        "success": True,
        "keys": stored_settings.get("api_keys", {})
    }), 200

@app.route('/api/keys', methods=['POST'])
def add_api_key():
    """Add or update API key"""
    try:
        data = request.get_json()
        name = data.get("name")
        key = data.get("key")
        
        if not name or not key:
            return jsonify({
                "success": False,
                "error": "Name and key are required"
            }), 400
        
        if "api_keys" not in stored_settings:
            stored_settings["api_keys"] = {}
        
        stored_settings["api_keys"][name] = key
        
        return jsonify({
            "success": True,
            "message": f"API key '{name}' saved",
            "keys": stored_settings["api_keys"]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/keys/<key_name>', methods=['DELETE'])
def delete_api_key(key_name):
    """Delete API key"""
    try:
        if key_name in stored_settings.get("api_keys", {}):
            del stored_settings["api_keys"][key_name]
            return jsonify({
                "success": True,
                "message": f"API key '{key_name}' deleted"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"API key '{key_name}' not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# ============================================================================
# TICKER ENDPOINTS
# ============================================================================

@app.route('/api/tickers', methods=['GET'])
def get_tickers():
    """Get all tickers"""
    return jsonify({
        "success": True,
        "tickers": stored_settings.get("tickers", []),
        "count": len(stored_settings.get("tickers", []))
    }), 200

@app.route('/api/tickers', methods=['POST'])
def add_ticker():
    """Add ticker"""
    try:
        data = request.get_json()
        ticker = data.get("ticker", "").upper()
        
        if not ticker:
            return jsonify({
                "success": False,
                "error": "Ticker symbol is required"
            }), 400
        
        if "tickers" not in stored_settings:
            stored_settings["tickers"] = []
        
        if ticker not in stored_settings["tickers"]:
            stored_settings["tickers"].append(ticker)
            return jsonify({
                "success": True,
                "message": f"Ticker '{ticker}' added",
                "tickers": stored_settings["tickers"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Ticker '{ticker}' already exists"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/tickers/<ticker>', methods=['DELETE'])
def delete_ticker(ticker):
    """Delete ticker"""
    try:
        ticker = ticker.upper()
        if ticker in stored_settings.get("tickers", []):
            stored_settings["tickers"].remove(ticker)
            return jsonify({
                "success": True,
                "message": f"Ticker '{ticker}' deleted"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Ticker '{ticker}' not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# ============================================================================
# DATA ENDPOINTS
# ============================================================================

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get stored data"""
    return jsonify({
        "success": True,
        "data": stored_data,
        "last_update": stored_data.get("last_update")
    }), 200

@app.route('/api/data/<ticker>', methods=['GET'])
def get_ticker_data(ticker):
    """Get data for specific ticker"""
    ticker = ticker.upper()
    if ticker in stored_data.get("tickers", {}):
        return jsonify({
            "success": True,
            "ticker": ticker,
            "data": stored_data["tickers"][ticker]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": f"No data for ticker '{ticker}'"
        }), 404

@app.route('/api/data', methods=['POST'])
def store_data():
    """Store data"""
    try:
        data = request.get_json()
        
        if "tickers" in data:
            stored_data["tickers"] = data["tickers"]
        
        stored_data["last_update"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "message": "Data stored successfully",
            "last_update": stored_data["last_update"]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export data as CSV format"""
    try:
        csv_data = "Ticker,Value,Timestamp\n"
        
        for ticker, data in stored_data.get("tickers", {}).items():
            csv_data += f"{ticker},{data.get('value', 'N/A')},{stored_data.get('last_update', 'N/A')}\n"
        
        return jsonify({
            "success": True,
            "format": "csv",
            "data": csv_data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/export/json', methods=['GET'])
def export_json():
    """Export data as JSON"""
    return jsonify({
        "success": True,
        "format": "json",
        "data": stored_data
    }), 200

# ============================================================================
# STATUS ENDPOINTS
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status"""
    return jsonify({
        "success": True,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "tickers_count": len(stored_settings.get("tickers", [])),
            "api_keys_count": len(stored_settings.get("api_keys", {})),
            "data_entries": len(stored_data.get("tickers", {})),
            "last_data_update": stored_data.get("last_update")
        }
    }), 200

# ============================================================================
# ERROR HANDLING
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "path": request.path
    }), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
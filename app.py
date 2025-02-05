from flask import Flask, jsonify
import json
import os
from main import main  # Import the main scraping function
import threading

app = Flask(__name__)

# Load the menu structure
with open('menu_structure.json', 'r') as f:
    menu_data = json.load(f)

# Track scraping status
scraping_status = {
    "is_running": False,
    "last_run": None,
    "status": "idle"
}

def run_scraper():
    global scraping_status
    try:
        scraping_status["is_running"] = True
        scraping_status["status"] = "running"
        main()  # Run the main scraping function
        scraping_status["status"] = "completed"
    except Exception as e:
        scraping_status["status"] = f"failed: {str(e)}"
    finally:
        scraping_status["is_running"] = False
        from datetime import datetime
        scraping_status["last_run"] = datetime.now().isoformat()

@app.route('/')
def home():
    return "Fouani Store API is running!"

@app.route('/api/menu', methods=['GET'])
def get_menu():
    return jsonify(menu_data)

@app.route('/api/scrape', methods=['GET'])
def start_scrape():
    global scraping_status
    if scraping_status["is_running"]:
        return jsonify({
            "message": "Scraping already in progress",
            "status": scraping_status
        }), 409
    
    # Start scraping in a background thread
    thread = threading.Thread(target=run_scraper)
    thread.start()
    
    return jsonify({
        "message": "Scraping process started",
        "status": scraping_status
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(scraping_status)

# This ensures the scraping doesn't start automatically
if __name__ == '__main__':
    # Get port from environment variable or default to 10000
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 
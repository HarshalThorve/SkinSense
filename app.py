"""
SkinSense Application Entry Point
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print(f"SkinSense Application Initializing on port {port}...")
    app.run(debug=debug, host="0.0.0.0", port=port)

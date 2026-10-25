import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    print(f"""
    ========================================================
     GROWLYTICS - AI-POWERED RETAIL INTELLIGENCE PLATFORM
     "Turn Insights Into Growth"
    ========================================================
     * Serving on http://127.0.0.1:{port}
     * Environment: {app.config.get('ENV', 'development')}
     * Database: {app.config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1] if '@' in app.config.get('SQLALCHEMY_DATABASE_URI', '') else 'Local SQLite'}
    ========================================================
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)

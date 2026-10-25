import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from backend.config import Config
from backend.extensions import db, cors

# Import API blueprints
from backend.routes.auth import auth_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.inventory import inventory_bp
from backend.routes.sales import sales_bp
from backend.routes.copilot import copilot_bp
from backend.seed import seed_database


def create_app(config_class=Config):
    """Application factory for Growlytics."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(copilot_bp)

    # Ensure tables exist and seed demo catalog safely if empty
    with app.app_context():
        try:
            db.create_all()
            # Seed only if database is completely empty; never overwrite user data
            seed_database()
        except Exception as e:
            app.logger.warning(f"Database schema initialization note: {e}")

    # Health and Diagnostic Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        db_connected = False
        db_type = "unknown"
        error_msg = None
        try:
            # Test live query
            from backend.models import Product
            count = Product.query.count()
            db_connected = True
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            db_type = "PostgreSQL" if "postgres" in uri else ("SQLite" if "sqlite" in uri else "Relational DB")
        except Exception as e:
            error_msg = str(e)

        return jsonify({
            "status": "healthy" if db_connected else "degraded",
            "app": "Growlytics Retail Intelligence",
            "version": "1.0.0",
            "environment": app.config.get("ENV", "development"),
            "database": {
                "connected": db_connected,
                "type": db_type,
                "error": error_msg
            },
            "timestamp": app.config.get("IS_VERCEL")
        }), 200 if db_connected else 500

    # Resolve frontend directory path
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    # Serve HTML pages
    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<page_name>")
    def render_page(page_name):
        # Prevent accessing hidden files
        if page_name.startswith("."):
            return jsonify({"error": "Not found"}), 404

        # Direct file check (e.g., favicon.ico, manifest.json)
        target_file = frontend_dir / page_name
        if target_file.is_file():
            return send_from_directory(frontend_dir, page_name)

        # HTML page check (e.g., /inventory -> inventory.html)
        html_file = frontend_dir / f"{page_name}.html"
        if html_file.is_file():
            return send_from_directory(frontend_dir, f"{page_name}.html")

        # API fallback check
        if page_name.startswith("api"):
            return jsonify({"error": "API route not found"}), 404

        return send_from_directory(frontend_dir, "index.html")

    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(frontend_dir / "css", filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(frontend_dir / "js", filename)

    # API Error Handlers
    @app.errorhandler(404)
    def not_found_handler(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Endpoint not found"}), 404
        return send_from_directory(frontend_dir, "index.html")

    @app.errorhandler(500)
    def internal_error_handler(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error occurred."}), 500
        return "An internal server error occurred.", 500

    return app

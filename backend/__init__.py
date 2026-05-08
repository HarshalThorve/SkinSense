"""
SkinSense Backend — Flask Application Factory
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static')
    )

    # Load configuration
    from backend.config import Config
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register template filters
    @app.template_filter('ist')
    def utc_to_ist(dt):
        import datetime
        if not dt:
            return None
        return dt + datetime.timedelta(hours=5, minutes=30)

    # Register blueprints
    from backend.routes.auth import auth_bp
    from backend.routes.main import main_bp
    from backend.routes.analysis import analysis_bp
    from backend.routes.ingredients import ingredients_bp
    from backend.routes.trends import trends_bp
    from backend.routes.reports import reports_bp
    from backend.routes.pages import pages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(ingredients_bp)
    app.register_blueprint(trends_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(pages_bp)

    # Create database tables
    with app.app_context():
        from backend import models  # noqa: F401
        # Ensure instance directory exists for SQLite
        instance_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
        os.makedirs(instance_path, exist_ok=True)
        db.create_all()

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app

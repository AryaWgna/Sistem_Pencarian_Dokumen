from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Silakan login terlebih dahulu.'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MODEL_DIR'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dokumen import dokumen_bp
    from app.routes.pencarian import pencarian_bp
    from app.routes.riwayat import riwayat_bp
    from app.routes.metodologi import metodologi_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dokumen_bp, url_prefix='/dokumen')
    app.register_blueprint(pencarian_bp)
    app.register_blueprint(riwayat_bp)
    app.register_blueprint(metodologi_bp, url_prefix='/metodologi')

    return app

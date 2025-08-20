import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "crypto-monitor-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///crypto_monitor.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

with app.app_context():
    # Import models to ensure they're registered
    import models
    db.create_all()

# Import routes after app creation
import routes

# Start monitoring service in background thread
import threading
from monitor import start_monitoring

def start_background_monitoring():
    """Start monitoring in a daemon thread"""
    monitoring_thread = threading.Thread(target=start_monitoring, daemon=True, name="CryptoMonitor")
    monitoring_thread.start()
    logging.info("Background crypto monitoring started")

# Start monitoring when app starts
start_background_monitoring()

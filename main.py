from app import app, socketio
from monitor import start_monitoring
import threading
import logging

if __name__ == '__main__':
    # Start the monitoring service in a separate thread
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()
    logging.info("Crypto monitoring service started")
    
    # Start the Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True, use_reloader=False, log_output=True)

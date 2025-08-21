from app import app, socketio
from monitor import start_monitoring as original_start_monitoring
import threading
import logging

# ruaj kontratat e postuara
posted_contracts = set()

def start_monitoring():
    global posted_contracts
    for token in original_start_monitoring():  # supozojmë që monitor.py gjeneron tokena
        contract_address = token.get("contract")
        if contract_address and contract_address not in posted_contracts:
            # vetëm një herë dërgohet
            message = telegram_bot.format_token_message(
                token_name=token.get("name"),
                contract_address=contract_address
            )
            buy_button = telegram_bot.create_buy_button(token.get("pool_id"))

            telegram_bot.send_message(message, reply_markup=buy_button)
            posted_contracts.add(contract_address)

if __name__ == '__main__':
    # Start the monitoring service in a separate thread
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()
    logging.info("Crypto monitoring service started")

    # Start the Flask-SocketIO server
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,              # mos përdor debug=True në server prodhimi
        allow_unsafe_werkzeug=True,
        use_reloader=False,       # 🚨 ky ndalon nisjen e procesit të dytë
        log_output=True
    )

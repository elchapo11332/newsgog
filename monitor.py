import logging
import requests
import time
from typing import Optional

from app import app, db, socketio
from models import PostedToken
from telegram_bot import telegram_bot


class CryptoMonitor:
    def __init__(self):
        self.api_url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
        self.check_interval = 30  # seconds
        self.running = False
        self.posted_cache = set()  # ✅ cache lokale për shmangie të dyfishtë

    def is_token_posted(self, contract_address: str) -> bool:
        """Check në cache + DB nëse është postuar më parë"""
        if contract_address in self.posted_cache:
            return True

        with app.app_context():
            exists = (
                PostedToken.query.filter_by(contract_address=contract_address).first()
                is not None
            )
            if exists:
                self.posted_cache.add(contract_address)  # ✅ fut në cache
            return exists

    def save_posted_token(
        self, name: str, contract_address: str, telegram_message_id: Optional[str] = None
    ):
        """Ruaj token në DB dhe cache"""
        if contract_address in self.posted_cache:
            return None  # ✅ mos fut dy herë

        with app.app_context():
            token = PostedToken(
                name=name,
                contract_address=contract_address,
                telegram_message_id=telegram_message_id,
            )
            db.session.add(token)
            db.session.commit()

            # ✅ update cache
            self.posted_cache.add(contract_address)

            # Emit në WebSocket
            socketio.emit("new_token", token.to_dict())

            return token

    def fetch_tokens(self):
        """Merr tokenat nga API"""
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching tokens: {e}")
            return []

    def process_token(self, token: dict):
        """Proceson një token të ri"""
        try:
            contract_address = token.get("coinType")
            name = token.get("name", "Unknown")

            if not contract_address:
                return

            # ✅ Skip nëse është postuar
            if self.is_token_posted(contract_address):
                logging.debug(f"Skipping already posted token: {contract_address}")
                return

            # Përgatit mesazhin
            message = telegram_bot.format_token_message(name, contract_address)

            # Butoni BUY
            reply_markup = telegram_bot.create_buy_button(pool_id=token.get("id", ""))

            # Dërgo në Telegram
            result = telegram_bot.send_message(message, reply_markup=reply_markup)

            if result:
                telegram_message_id = result.get("message_id")
                self.save_posted_token(name, contract_address, telegram_message_id)
                logging.info(f"Posted new token: {name} ({contract_address})")

        except Exception as e:
            logging.error(f"Error processing token: {e}")

    def run(self):
        """Loop kryesor i monitorimit"""
        self.running = True
        logging.info("Crypto monitor started")

        while self.running:
            tokens = self.fetch_tokens()
            for token in tokens:
                self.process_token(token)
            time.sleep(self.check_interval)


def start_monitoring():
    monitor = CryptoMonitor()
    monitor.run()

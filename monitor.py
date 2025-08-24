import requests
import time
import logging
from datetime import datetime
from typing import Optional
from app import app, db, socketio
from models import PostedToken, MonitorStats
from telegram_bot import telegram_bot
from flask_socketio import emit


class CryptoMonitor:
    def __init__(self):
        self.api_url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
        self.check_interval = 30  # seconds
        self.running = False

    def get_stats(self):
        with app.app_context():
            stats = MonitorStats.query.first()
            if not stats:
                stats = MonitorStats()
                db.session.add(stats)
                db.session.commit()
            return stats

    def update_stats(self, **kwargs):
        with app.app_context():
            stats = self.get_stats()
            for key, value in kwargs.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            db.session.commit()
            socketio.emit("stats_update", stats.to_dict())

    def is_token_posted(self, contract_address: str) -> bool:
        with app.app_context():
            return (
                PostedToken.query.filter_by(contract_address=contract_address).first()
                is not None
            )

    def save_posted_token(
        self, name: str, contract_address: str, telegram_message_id: Optional[str] = None
    ):
        with app.app_context():
            token = PostedToken(
                name=name,
                contract_address=contract_address,
                telegram_message_id=telegram_message_id,
            )
            db.session.add(token)
            db.session.commit()
            socketio.emit("new_token", token.to_dict())
            return token

    def fetch_tokens(self):
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("pools", [])
        except Exception as e:
            logging.error(f"Error fetching tokens: {e}")
            return []

    def process_tokens(self, tokens):
        new_tokens_count = 0
        posted_tokens_count = 0

        for pool in tokens:
            try:
                coin_metadata = pool.get("coinMetadata", {})
                name = (
                    coin_metadata.get("name")
                    or coin_metadata.get("symbol")
                    or pool.get("name")
                    or pool.get("symbol")
                )
                if not name or name.strip() == "":
                    name = "Unknown Token"
                else:
                    name = str(name).strip()

                contract = pool.get("coinType")
                pool_id = pool.get("poolId")
                metadata = pool.get("metadata", {})
                twitter_handle = metadata.get("CreatorTwitterName")
                dev_wallet = pool.get("creatorAddress")  # shtova DEV WALLET
                token_image = coin_metadata.get("icon_url") or coin_metadata.get("iconUrl")

                if not contract:
                    continue

                new_tokens_count += 1

                # MOS POSTO DUPLIKAT
                if self.is_token_posted(contract):
                    logging.debug(f"Token already posted: {name} ({contract})")
                    continue

                if name == "Unknown Token":
                    continue

                message = telegram_bot.format_token_message(
                    name, contract, twitter_handle, pool_id, dev_wallet
                )
                buy_button = telegram_bot.create_buy_button(pool_id) if pool_id else None

                if token_image and token_image.startswith("data:image"):
                    telegram_result = telegram_bot.send_photo(
                        token_image, message, buy_button
                    )
                else:
                    telegram_result = telegram_bot.send_message(message, buy_button)

                if telegram_result:
                    message_id = str(telegram_result.get("message_id", ""))
                    self.save_posted_token(name, contract, message_id)
                    posted_tokens_count += 1
            except Exception as e:
                logging.error(f"Error processing pool: {e}")
                continue

        return new_tokens_count, posted_tokens_count

    def monitor_loop(self):
        logging.info("Starting crypto monitoring loop")
        self.running = True
        self.update_stats(is_running=True)

        while self.running:
            try:
                tokens = self.fetch_tokens()
                new_count, posted_count = self.process_tokens(tokens)
                stats = self.get_stats()
                self.update_stats(
                    total_tokens_found=stats.total_tokens_found + new_count,
                    total_tokens_posted=stats.total_tokens_posted + posted_count,
                    last_check=datetime.utcnow(),
                    last_error=None,
                )
                logging.info(
                    f"Check complete. Found: {new_count}, Posted: {posted_count}"
                )
            except Exception as e:
                error_msg = f"Monitor error: {str(e)}"
                logging.error(error_msg)
                self.update_stats(last_check=datetime.utcnow(), last_error=error_msg)
                socketio.emit("monitor_error", {"error": error_msg})

            time.sleep(self.check_interval)

        self.update_stats(is_running=False)
        logging.info("Monitoring loop stopped")

    def stop(self):
        self.running = False


# Global monitor instance
monitor = CryptoMonitor()


def start_monitoring():
    """Start monitoring service (exported for import in main.py)"""
    try:
        monitor.monitor_loop()
    except Exception as e:
        logging.error(f"Fatal error in monitoring service: {e}")

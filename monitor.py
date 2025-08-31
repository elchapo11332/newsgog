import requests
import time
import logging
from datetime import datetime
from typing import Optional
from app import app, db, socketio
from models import PostedToken, MonitorStats
from telegram_bot import TelegramBot
from flask_socketio import emit


class CryptoMonitor:
    def __init__(self):
        self.api_url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
        self.check_interval = 15  # seconds
        self.running = False
        self.telegram = TelegramBot()  # instanca e Telegram bot

    # ====================== DB & Stats ======================
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
            socketio.emit('stats_update', stats.to_dict())

    # ====================== Token Utils ======================
    def is_token_posted(self, contract_address: str) -> bool:
        with app.app_context():
            return (
                PostedToken.query.filter_by(contract_address=contract_address.lower()).first()
                is not None
            )

    def save_posted_token(self, name: str, contract_address: str, telegram_message_id: Optional[str] = None):
        with app.app_context():
            token = PostedToken(
                name=name,
                contract_address=contract_address.lower(),
                telegram_message_id=telegram_message_id,
            )
            db.session.add(token)
            db.session.commit()
            socketio.emit("new_token", token.to_dict())
            return token

    # ====================== API Fetch ======================
    def fetch_tokens(self):
        try:
            response = requests.get(self.api_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("pools", [])
        except Exception as e:
            logging.error(f"Error fetching tokens: {e}")
            return []

    # ====================== Process Tokens ======================
    def process_tokens(self, tokens):
        new_tokens_count = 0
        posted_tokens_count = 0

        for pool in tokens:
            try:
                contract = pool.get("coinType")
                if not contract:
                    continue
                contract = contract.lower()

                if self.is_token_posted(contract):
                    logging.debug(f"Already posted: {contract}")
                    continue

                # Extract token info
                coin_metadata = pool.get("coinMetadata") or {}
                name = (
                    coin_metadata.get("name")
                    or coin_metadata.get("symbol")
                    or pool.get("name")
                    or pool.get("symbol")
                    or "Unknown Token"
                ).strip()
                if name == "Unknown Token":
                    logging.warning(f"Skipping unknown token: {contract}")
                    continue

                pool_id = pool.get("coinType")

                # Extract socials
                creator_data = pool.get("creatorData") or {}
                twitter_handle = creator_data.get("twitterHandle")
                telegram_handle = creator_data.get("telegramHandle")
                socials = {}
                if twitter_handle:
                    socials["twitter"] = f"https://x.com/{twitter_handle.lstrip('@').strip()}"
                if telegram_handle:
                    socials["telegram"] = telegram_handle

                # Other info
                token_image = coin_metadata.get("icon_url") or coin_metadata.get("iconUrl")
                creator_address = pool.get("creatorAddress")
                market_data = pool.get("marketData") or {}

                # Rregullo MarketCap
                market_cap_value = market_data.get("marketCap")
                if market_cap_value is not None:
                    try:
                        market_cap = f"{int(round(float(market_cap_value))):,}"
                    except Exception:
                        market_cap = str(market_cap_value)
                else:
                    market_cap = "N/A"

                is_protected = pool.get("isProtected", False)
                description = coin_metadata.get("description") or pool.get("description") or "N/A"

                # Dev Initial Buy
                creator_balance = pool.get("creatorBalance")
                creator_percent = pool.get("creatorPercent")
                dev_buy_text = None
                if creator_balance is not None:
                    try:
                        balance_int = int(round(float(creator_balance)))
                        dev_buy_text = f"Dev Initial: {balance_int:,} tokens"
                        if creator_percent is not None:
                            dev_buy_text += f" ({creator_percent}%)"
                    except Exception:
                        dev_buy_text = f"Dev Initial: {creator_balance} tokens"

                logging.warning(
                    f"📢 Preparing to post token: {name} ({contract}) | "
                    f"MarketCap: {market_cap} | Protected: {is_protected} | "
                    f"Dev: {dev_buy_text or 'N/A'} | X: {twitter_handle or 'N/A'} | TG: {telegram_handle or 'N/A'}"
                )

                # Build Telegram message
                message = self.telegram.format_token_message(
                    token_name=name,
                    symbol=coin_metadata.get("symbol", ""),
                    contract_address=contract,
                    coinType=pool_id,
                    creator_address=creator_address,
                    socials=socials if socials else None,
                    is_protected=is_protected,
                    description=description,
                    market_cap=market_cap,
                    dev_initial_buy=dev_buy_text
                )

                # Create buy button
                buy_button = self.telegram.create_buy_button(pool_id) if pool_id else None

                # Post to Telegram
                if token_image and token_image.startswith("data:image"):
                    telegram_result = self.telegram.send_photo(token_image, message, buy_button)
                else:
                    telegram_result = self.telegram.send_message(message, buy_button)

                if telegram_result:
                    message_id = str(telegram_result.get("message_id", ""))
                    self.save_posted_token(name, contract, message_id)
                    posted_tokens_count += 1
                    new_tokens_count += 1
                    logging.info(f"✅ Posted: {name} (msg id {message_id})")
                else:
                    logging.error(f"❌ Failed to post {name}")

            except Exception as e:
                logging.error(f"Error processing pool {contract}: {e}")
                continue

        return new_tokens_count, posted_tokens_count

    # ====================== Monitor Loop ======================
    def monitor_loop(self):
        if self.running:
            logging.warning("Monitor loop already running, skipping...")
            return

        logging.info("Starting monitor loop")
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

                logging.info(f"Cycle complete. Found: {new_count}, Posted: {posted_count}")

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


# ====================== Global Monitor ======================
monitor = CryptoMonitor()


def start_monitoring():
    if monitor.running:
        logging.warning("Monitor already running, skipping start")
        return
    try:
        monitor.monitor_loop()
    except Exception as e:
        logging.error(f"Fatal error in monitor: {e}")

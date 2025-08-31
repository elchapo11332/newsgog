# ================= Telegram Bot =================
import os
import json
import logging
import requests
import base64
import tempfile
from typing import Optional, Dict


class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
        chat_id_env = os.getenv("CHAT_ID", "-1002928353318")
        self.chat_id = chat_id_env if chat_id_env.startswith('-') else f'-{chat_id_env}'
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get('ok'):
                logging.info(f"Message sent: {text[:50]}...")
                return result.get('result')
            logging.error(f"Telegram API error: {result}")
            return None
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return None

    def send_photo(self, photo_data: str, caption: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        try:
            if photo_data.startswith('data:image'):
                header, encoded = photo_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(image_bytes)
                    temp_file.flush()
                    url = f"{self.api_url}/sendPhoto"
                    files = {'photo': open(temp_file.name, 'rb')}
                    data = {
                        'chat_id': self.chat_id,
                        'caption': caption,
                        'parse_mode': 'HTML'
                    }
                    if reply_markup:
                        data['reply_markup'] = json.dumps(reply_markup)
                    response = requests.post(url, files=files, data=data, timeout=30)
                    files['photo'].close()
                    os.unlink(temp_file.name)
                    response.raise_for_status()
                    result = response.json()
                    if result.get('ok'):
                        logging.info(f"Photo sent: {caption[:50]}...")
                        return result.get('result')
                    logging.error(f"Telegram API error sending photo: {result}")
                    return None
            logging.error("Unsupported photo format")
            return None
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
            return None

    def format_token_message(
        self,
        token_name: str,
        symbol: str,
        contract_address: str,
        coinType: str,
        creator_address: str,
        socials: Optional[Dict[str, str]] = None,
        is_protected: Optional[bool] = None,
        description: Optional[str] = None,
        market_cap: Optional[float] = None,
        dev_initial_buy: Optional[str] = None
    ) -> str:
        message = f"📣 <b>{token_name.upper()}</b>\n"
        message += f"deployed on <a href='https://blast.fun'>Blast.fun</a> 🆕!\n\n"
        message += f"🪙 <b>{token_name} - ${symbol}</b>\n"
        message += f"<code>{contract_address}</code>\n<code>{coinType}</code>\n\n"
        if description:
            message += f"📝 <b>Description:</b> {description}\n\n"
        if market_cap is not None:
            message += f"💰 <b>Market Cap:</b> {market_cap}\n\n"
        if dev_initial_buy:
            message += f"⚡ <b>{dev_initial_buy}</b>\n\n"
        if socials:
            links = []
            if "twitter" in socials:
                links.append(f"🐦 <a href='{socials['twitter']}'>X</a>")
            if "telegram" in socials:
                links.append(f"📢 <a href='{socials['telegram']}'>TG</a>")
            message += f"📊 <b>Socials:</b> " + " | ".join(links) + "\n\n"
        if is_protected is True:
            message += "🚨 <b>Anti-Sniper Protection Active</b>\n\n"
        elif is_protected is False:
            message += "⚠️ <b>Anti-Sniper NOT Active</b>\n\n"
        message += f"👨‍💻 <b>Created By:</b> <a href='https://suiscan.xyz/mainnet/account/{creator_address}'>{creator_address[:6]}...{creator_address[-4:]}</a>"
        return message

    def create_buy_button(self, coinType: str) -> dict:
        return {
            "inline_keyboard": [
                [{"text": "🚀 BUY TOKEN", "url": f"https://t.me/RaidenXTradeBot?start=Blastn_sw_{coinType[:20]}"}]
            ]
        }


# Global instance
telegram_bot = TelegramBot()


# ================= CryptoMonitor =================
import requests
import time
import logging
from datetime import datetime
from typing import Optional
from app import app, db, socketio
from models import PostedToken, MonitorStats
from flask_socketio import emit


class CryptoMonitor:
    def __init__(self):
        self.api_url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
        self.check_interval = 15
        self.running = False
        self.telegram = telegram_bot

    # DB & Stats
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

    # Token Utils
    def is_token_posted(self, contract_address: str) -> bool:
        with app.app_context():
            return PostedToken.query.filter_by(contract_address=contract_address.lower()).first() is not None

    def save_posted_token(self, name: str, contract_address: str, telegram_message_id: Optional[str] = None):
        with app.app_context():
            token = PostedToken(name=name, contract_address=contract_address.lower(), telegram_message_id=telegram_message_id)
            db.session.add(token)
            db.session.commit()
            socketio.emit("new_token", token.to_dict())
            return token

    # API Fetch
    def fetch_tokens(self):
        try:
            response = requests.get(self.api_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("pools", [])
        except Exception as e:
            logging.error(f"Error fetching tokens: {e}")
            return []

    # Process Tokens
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
                    continue

                coin_metadata = pool.get("coinMetadata") or {}
                name = (coin_metadata.get("name") or coin_metadata.get("symbol") or pool.get("name") or pool.get("symbol") or "Unknown Token").strip()
                if name == "Unknown Token":
                    continue

                pool_id = pool.get("coinType")

                # Socials
                creator_data = pool.get("creatorData") or {}
                twitter = creator_data.get("twitterHandle")
                telegram_handle = creator_data.get("telegramHandle")
                socials = {}
                if twitter:
                    socials["twitter"] = f"https://x.com/{twitter.lstrip('@').strip()}"
                if telegram_handle:
                    socials["telegram"] = telegram_handle

                token_image = coin_metadata.get("icon_url") or coin_metadata.get("iconUrl")
                creator_address = pool.get("creatorAddress")
                market_data = pool.get("marketData") or {}
                market_cap = market_data.get("marketCap")
                is_protected = pool.get("isProtected", False)
                description = coin_metadata.get("description") or pool.get("description") or "N/A"

                # Dev Buy
                creator_balance = pool.get("creatorBalance")
                creator_percent = pool.get("creatorPercent")
                dev_buy_text = None
                if creator_balance:
                    dev_buy_text = f"Dev Initial: {creator_balance:,} tokens"
                    if creator_percent:
                        dev_buy_text += f" ({creator_percent}%)"

                # Telegram message
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

                buy_button = self.telegram.create_buy_button(pool_id) if pool_id else None

                # Send Telegram
                if token_image and token_image.startswith("data:image"):
                    telegram_result = self.telegram.send_photo(token_image, message, buy_button)
                else:
                    telegram_result = self.telegram.send_message(message, buy_button)

                if telegram_result:
                    message_id = str(telegram_result.get("message_id", ""))
                    self.save_posted_token(name, contract, message_id)
                    new_tokens_count += 1
                    posted_tokens_count += 1

            except Exception as e:
                logging.error(f"Error processing pool {pool.get('coinType')}: {e}")
                continue

        return new_tokens_count, posted_tokens_count

    # Monitor Loop
    def monitor_loop(self):
        if self.running:
            logging.warning("Monitor loop already running")
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
                    last_error=None
                )
                logging.info(f"Cycle complete. Found: {new_count}, Posted: {posted_count}")
            except Exception as e:
                error_msg = f"Monitor error: {e}"
                logging.error(error_msg)
                self.update_stats(last_check=datetime.utcnow(), last_error=error_msg)
                socketio.emit("monitor_error", {"error": error_msg})
            time.sleep(self.check_interval)

        self.update_stats(is_running=False)
        logging.info("Monitor stopped")

    def stop(self):
        self.running = False


# Global monitor
monitor = CryptoMonitor()


def start_monitoring():
    if monitor.running:
        logging.warning("Monitor already running")
        return
    try:
        monitor.monitor_loop()
    except Exception as e:
        logging.error(f"Fatal error in monitor: {e}")

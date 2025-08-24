import os
import requests
import logging

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def format_token_message(self, name, contract, twitter_handle=None, pool_id=None, dev_wallet=None):
        msg = f"🚀 <b>{name}</b>\n\n"
        msg += f"🔹 Contract: <code>{contract}</code>\n"
        if pool_id:
            msg += f"💧 Pool ID: <code>{pool_id}</code>\n"
        if twitter_handle:
            msg += f"🐦 Twitter: @{twitter_handle}\n"
        if dev_wallet:
            msg += f"👤 Dev Wallet: <code>{dev_wallet}</code>\n"
        return msg

    def create_buy_button(self, pool_id):
        return {
            "inline_keyboard": [[
                {"text": "🟢 BUY", "url": f"https://suiscan.xyz/pool/{pool_id}"}
            ]]
        }

    def send_message(self, text, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as e:
            logging.error(f"Telegram send_message error: {e}")
            return None

    def send_photo(self, photo, caption, reply_markup=None):
        url = f"{self.base_url}/sendPhoto"
        payload = {
            "chat_id": self.chat_id,
            "caption": caption,
            "parse_mode": "HTML",
            "photo": photo
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as e:
            logging.error(f"Telegram send_photo error: {e}")
            return None

telegram_bot = TelegramBot()

import os
import json
import logging
import requests
import base64
import tempfile
from typing import Optional


class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "8315223590:AAGOsygmRT9y_DjOxueYnRikPo1i9Gxxjk4")
        chat_id_env = os.getenv("CHAT_ID", "-1003083174899")
        self.chat_id = chat_id_env if chat_id_env.startswith('-') else f'-{chat_id_env}'
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.suivision_api = "https://api.suivision.xyz/v1"

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
                payload['reply_markup'] = reply_markup
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get('ok'):
                logging.info(f"Message sent successfully: {text[:50]}...")
                return result.get('result')
            else:
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
                        logging.info(f"Photo sent successfully: {caption[:50]}...")
                        return result.get('result')
                    else:
                        logging.error(f"Telegram API error sending photo: {result}")
                        return None
            else:
                logging.error("Unsupported photo format - only base64 data URLs supported")
                return None
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
            return None

    def get_followers(self, contract_address: str) -> Optional[int]:
        """Fetch followers from SuiVision API"""
        try:
            url = f"{self.suivision_api}/token/{contract_address}/social"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("twitterFollowers", 0)
        except Exception as e:
            logging.error(f"Error fetching followers: {e}")
            return None

    def get_dev_initial_buy(self, creator_address: str) -> Optional[str]:
        """Fetch Dev initial buy transactions from SuiVision"""
        try:
            url = f"{self.suivision_api}/account/{creator_address}/transactions"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            for tx in data.get("data", []):
                if tx.get("type") == "coin::join_pool":
                    return f"{tx.get('amount', '0')} SUI"
            return None
        except Exception as e:
            logging.error(f"Error fetching dev initial buy: {e}")
            return None

    def format_token_message(
        self,
        token_name: str,
        contract_address: str,
        twitter_handle: Optional[str] = None,
        coinType: Optional[str] = None,
        creator_address: Optional[str] = None,
        market_cap: Optional[float] = None,
        is_protected: Optional[bool] = None
    ) -> str:

        followers = self.get_followers(contract_address)
        dev_initial_buy = self.get_dev_initial_buy(creator_address) if creator_address else None

        message = f"""🆕 <b>New Token Detected!</b>

📛 <b>Name:</b> {token_name}
📜 <b>Contract:</b> <code>{contract_address}</code>"""

        if twitter_handle:
            message += f"\n❌ <b>X:</b> <a href=\"https://x.com/{twitter_handle}\">@{twitter_handle}</a>"

        if followers is not None:
            message += f"\n👥 <b>Followers:</b> {followers:,}"

        if creator_address:
            message += f"\n👤 <b>Creator:</b> <a href=\"https://suivision.xyz/account/{creator_address}\">{creator_address[:6]}...{creator_address[-4:]}</a>"

        if market_cap is not None:
            message += f"\n💰 <b>MarketCap:</b> ${market_cap:,.2f}"

        if is_protected is not None:
            status = "✅ Protected" if is_protected else "⚠️ Not Protected"
            message += f"\n🛡️ <b>Security:</b> {status}"

        if dev_initial_buy:
            message += f"\n🛒 <b>Dev Initial Buy:</b> {dev_initial_buy}"

        return message

    def create_buy_button(self, coinType: str) -> dict:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 BUY TOKEN",
                        "url": f"https://t.me/RaidenXTradeBot?start=Blastn_sw_{coinType[:20]}"
                    }
                ]
            ]
        }


telegram_bot = TelegramBot()
 

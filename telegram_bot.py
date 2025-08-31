import os
import json
import logging
import requests
import base64
import tempfile
from typing import Optional, Dict


class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "8315223590:AAGOsygmRT9y_DjOxueYnRikPo1i9Gxxjk4")
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
        """Format token message with all fields: socials, description, market cap, dev buy, protection"""

        message = f"📣 <b>{token_name.upper()}</b>\n"
        message += f"deployed on <a href='https://blast.fun'>Blast.fun</a> 🆕!\n\n"

        message += f"🪙 <b>{token_name} - ${symbol}</b>\n\n"
        message += f"Ca:<code>{contract_address}</code>\n\n"

        if description:
            message += f"📝 <b>Description:</b> {description}\n\n"

        if market_cap:
            message += f"💰 <b>Market Cap:</b> ${market_cap:,}\n\n"

        if dev_initial_buy:
            message += f"👷 <b>Dev Initial Buy:</b> {dev_initial_buy}\n\n"

        if socials:
            links = []
            if "twitter" in socials:
                links.append(f"🐦 <a href='{socials['twitter']}'>X Account</a>")
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
                [
                    {"text": "🚀 BUY TOKEN", "url": f"https://t.me/RaidenXTradeBot?start=Blastn_sw_{coinType[:20]}"}
                ]
            ]
        }


# Global bot instance
telegram_bot = TelegramBot()

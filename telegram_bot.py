import os
import json
import logging
import requests
import base64
import tempfile
from typing import Optional, Dict, Any

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN", "8315223590:AAGOsygmRT9y_DjOxueYnRikPo1i9Gxxjk4")
        chat_id_env = os.getenv("CHAT_ID", "-1003083174899")
        # Ensure chat_id has negative sign for groups/channels
        self.chat_id = chat_id_env if chat_id_env.startswith('-') else f'-{chat_id_env}'
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        
        # Dev wallet API configuration
        self.wallet_api_key = os.getenv("WALLET_API_KEY", "default_api_key")
        self.wallet_api_url = os.getenv("WALLET_API_URL", "https://api.devwallet.com/v1")
        
    def send_message(self, text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        """Send a message to the configured Telegram chat"""
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
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error sending message: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error sending message: {e}")
            return None
    
    def send_photo(self, photo_data: str, caption: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        """Send a photo with caption to the configured Telegram chat"""
        try:
            # Handle base64 data URL
            if photo_data.startswith('data:image'):
                # Extract the base64 data
                header, encoded = photo_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(image_bytes)
                    temp_file.flush()
                    
                    # Send photo
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
                    
                    # Clean up temp file
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
    
    def get_creator_address(self, contract_address: str) -> Optional[str]:
        """Fetch creator address from dev wallet API"""
        try:
            # Use the specific API endpoint
            url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            pools = data.get('pools', [])
            
            # Search for the contract address in the pools
            for pool in pools:
                coin_type = pool.get('coinType', '')
                if contract_address in coin_type or coin_type == contract_address:
                    creator_address = pool.get('creatorAddress')
                    if creator_address:
                        logging.info(f"Retrieved creator address: {creator_address}")
                        return creator_address
            
            logging.warning(f"No creator address found for contract: {contract_address}")
            return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error fetching creator address: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching creator address: {e}")
            return None
    
    def format_token_message(self, token_name: str, contract_address: str, twitter_handle: Optional[str] = None, coinType: Optional[str] = None, creator_address: Optional[str] = None) -> str:
        """Format a new token message for Telegram with creator address information"""
        message = f"""🆕 <b>New Token Detected!</b>

📛 <b>Name:</b> {token_name}
📜 <b>Contract:</b> <code>{contract_address}</code>"""
        
        if twitter_handle:
            message += f"\n❌ <b>X:</b> <a href=\"https://x.com/{twitter_handle}\">@{twitter_handle}</a>"
        
        # Add creator address information if available
        if creator_address:
            # Create clickable link to Sui explorer
            sui_explorer_url = f"https://suiscan.xyz/mainnet/account/{creator_address}"
            message += f"\n👨‍💻 <b>Dev Wallet:</b> <a href=\"{sui_explorer_url}\">{creator_address[:8]}...{creator_address[-6:]}</a>"
        else:
            # If creator address fetch failed, still try to get it
            fetched_creator = self.get_creator_address(contract_address)
            if fetched_creator:
                sui_explorer_url = f"https://suiscan.xyz/mainnet/account/{fetched_creator}"
                message += f"\n👨‍💻 <b>Dev Wallet:</b> <a href=\"{sui_explorer_url}\">{fetched_creator[:8]}...{fetched_creator[-6:]}</a>"
            else:
                message += f"\n👨‍💻 <b>Dev Wallet:</b> <i>Not available</i>"
        
        return message
    
    def create_buy_button(self, pool_id: str, coinType: Optional[str] = None, creator_address: Optional[str] = None) -> dict:
        """Create inline keyboard with BUY button and wallet explorer link"""
        keyboard = []
        
        # Add buy button (always show) - use pool_id if coinType is not available
        if coinType:
            coin_param = coinType[:20]
        else:
            coin_param = pool_id[:20]
            
        keyboard.append([
            {
                "text": "🚀 BUY TOKEN",
                "url": f"https://t.me/RaidenXTradeBot?start=Blastn_sw_{coin_param}"
            }
        ])
        
        # Add wallet explorer button if creator address is available
        if creator_address:
            keyboard.append([
                {
                    "text": "👨‍💻 View Dev Wallet",
                    "url": f"https://suiscan.xyz/mainnet/account/{creator_address}"
                }
            ])
        
        return {
            "inline_keyboard": keyboard
        }
    
    def send_token_notification(self, token_name: str, contract_address: str, pool_id: str, twitter_handle: Optional[str] = None, coinType: Optional[str] = None) -> Optional[dict]:
        """Send a complete token notification with creator address information"""
        try:
            # Fetch creator address
            creator_address = self.get_creator_address(contract_address)
            
            # Format message with creator address
            message = self.format_token_message(
                token_name=token_name,
                contract_address=contract_address,
                twitter_handle=twitter_handle,
                coinType=coinType,
                creator_address=creator_address
            )
            
            # Create buttons including wallet explorer link
            reply_markup = self.create_buy_button(
                pool_id=pool_id,
                coinType=coinType,
                creator_address=creator_address
            )
            
            # Send the message
            return self.send_message(message, reply_markup)
            
        except Exception as e:
            logging.error(f"Error sending token notification: {e}")
            return None

# Create a global bot instance
telegram_bot = TelegramBot()

import os
import json
import logging
import requests
import base64
import tempfile
import hashlib
import time
from typing import Optional, Dict, Any, Set

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
        
        # Prevent duplicate posts with file-based persistence
        self.sent_messages_file = "sent_messages.json"
        self.processed_tokens_file = "processed_tokens.json"
        self.sent_messages: Set[str] = self._load_sent_messages()
        self.processed_tokens: Set[str] = self._load_processed_tokens()
        
    def _load_sent_messages(self) -> Set[str]:
        """Load sent messages from file"""
        try:
            if os.path.exists(self.sent_messages_file):
                with open(self.sent_messages_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('messages', []))
            return set()
        except Exception as e:
            logging.error(f"Error loading sent messages: {e}")
            return set()
    
    def _save_sent_messages(self):
        """Save sent messages to file"""
        try:
            with open(self.sent_messages_file, 'w') as f:
                json.dump({'messages': list(self.sent_messages)}, f)
        except Exception as e:
            logging.error(f"Error saving sent messages: {e}")
    
    def _load_processed_tokens(self) -> Set[str]:
        """Load processed tokens from file"""
        try:
            if os.path.exists(self.processed_tokens_file):
                with open(self.processed_tokens_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('tokens', []))
            return set()
        except Exception as e:
            logging.error(f"Error loading processed tokens: {e}")
            return set()
    
    def _save_processed_tokens(self):
        """Save processed tokens to file"""
        try:
            with open(self.processed_tokens_file, 'w') as f:
                json.dump({'tokens': list(self.processed_tokens)}, f)
        except Exception as e:
            logging.error(f"Error saving processed tokens: {e}")
    
    def _create_message_hash(self, text: str, reply_markup: Optional[dict] = None) -> str:
        """Create a unique hash for the message to prevent duplicates"""
        content = text + str(reply_markup) if reply_markup else text
        return hashlib.md5(content.encode()).hexdigest()
    
    def send_message(self, text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        """Send a message to the configured Telegram chat (prevents duplicates)"""
        try:
            # Create message hash to check for duplicates
            message_hash = self._create_message_hash(text, reply_markup)
            
            # Check if this message was already sent
            if message_hash in self.sent_messages:
                logging.warning(f"Duplicate message detected, skipping: {text[:50]}...")
                return None
            
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
                # Mark message as sent and save to file
                self.sent_messages.add(message_hash)
                self._save_sent_messages()
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
        """Fetch creator address from blast.fun API"""
        try:
            # Use the new blast.fun API endpoint for latest tokens
            url = "https://blast.fun/api/tokens?category=new&sortField=createdAt&sortDirection=DESC&pageSize=20"
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
    
    def get_latest_tokens(self) -> list:
        """Fetch latest new tokens from blast.fun API"""
        try:
            url = "https://steep-thunder-1d39.vapexmeli1.workers.dev/"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            pools = data.get('pools', [])
            
            logging.info(f"Retrieved {len(pools)} latest tokens")
            return pools
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error fetching latest tokens: {e}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error fetching latest tokens: {e}")
            return []
    
    def format_token_message(self, token_name: str, contract_address: str, twitter_handle: Optional[str] = None, coinType: Optional[str] = None, creator_address: Optional[str] = None) -> str:
        """Format a new token message for Telegram with creator address information"""
        message = f"""🆕 <b>New Token Detected!</b>

📛 <b>Name:</b> {token_name}
📜 <b>Contract:</b> <code>{contract_address}</code>"""
        
        if twitter_handle:
            message += f"\n❌ <b>X:</b> <a href=\"https://x.com/{twitter_handle}\">@{twitter_handle}</a>"
        
        # Always try to get creator address if not provided
        if not creator_address:
            # Try to get creator address from latest tokens API
            latest_tokens = self.get_latest_tokens()
            if latest_tokens:
                # Find matching token by contract address
                for pool in latest_tokens:
                    pool_contract = pool.get('coinType', '')
                    if contract_address in pool_contract or pool_contract == contract_address:
                        creator_address = pool.get('creatorAddress', '')
                        break
            
        # Add creator address information if available
        if creator_address:
            # Create clickable link to Sui explorer
            sui_explorer_url = f"https://suiscan.xyz/mainnet/account/{creator_address}"
            message += f"\n👨‍💻 <b>Dev Wallet:</b> <a href=\"{sui_explorer_url}\">{creator_address[:8]}...{creator_address[-6:]}</a>"
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
    
    def send_token_notification(self, token_name: str, contract_address: str, pool_id: str, twitter_handle: Optional[str] = None, coinType: Optional[str] = None, creator_address: Optional[str] = None) -> Optional[dict]:
        """Send a complete token notification with creator address information"""
        try:
            # Check if token already processed
            token_id = contract_address or pool_id
            if token_id in self.processed_tokens:
                logging.info(f"Token already processed, skipping: {token_name}")
                return None
            
            # Use provided creator_address or fetch it
            if not creator_address:
                creator_address = self.get_creator_address(contract_address)
            
            # Format the message with creator address information
            message = self.format_token_message(
                token_name=token_name,
                contract_address=contract_address,
                twitter_handle=twitter_handle,
                coinType=coinType,
                creator_address=creator_address
            )
            
            # Create buy button with wallet explorer link
            reply_markup = self.create_buy_button(
                pool_id=pool_id,
                coinType=coinType,
                creator_address=creator_address
            )
            
            # Send the message
            result = self.send_message(message, reply_markup)
            
            if result:
                # Mark token as processed
                self.processed_tokens.add(token_id)
                self._save_processed_tokens()
                logging.info(f"Successfully sent notification for token: {token_name}")
                return result
            else:
                logging.error(f"Failed to send notification for token: {token_name}")
                return None
                
        except Exception as e:
            logging.error(f"Error sending token notification: {e}")
            return None
    
    def monitor_new_tokens(self):
        """Monitor for new tokens and send notifications"""
        try:
            logging.info("Starting token monitoring...")
            
            while True:
                try:
                    # Get latest tokens
                    latest_tokens = self.get_latest_tokens()
                    
                    if not latest_tokens:
                        logging.warning("No tokens retrieved, waiting before retry...")
                        time.sleep(60)
                        continue
                    
                    # Process each token
                    for pool in latest_tokens:
                        try:
                            # Extract token information
                            token_name = pool.get('coinMetadata', {}).get('name', 'Unknown Token')
                            coin_type = pool.get('coinType', '')
                            pool_id = pool.get('poolId', '')
                            creator_address = pool.get('creatorAddress', '')
                            
                            # Extract Twitter handle from metadata if available
                            twitter_handle = None
                            metadata = pool.get('metadata', {})
                            if 'X' in metadata:
                                x_url = metadata['X']
                                # Extract handle from X URL
                                if 'x.com/' in x_url:
                                    twitter_handle = x_url.split('x.com/')[-1].split('?')[0].split('/')[0]
                            
                            # Use coinType as contract_address
                            contract_address = coin_type
                            
                            if not contract_address and not pool_id:
                                logging.warning(f"No contract address or pool ID for token: {token_name}")
                                continue
                            
                            # Send notification
                            self.send_token_notification(
                                token_name=token_name,
                                contract_address=contract_address,
                                pool_id=pool_id,
                                twitter_handle=twitter_handle if twitter_handle else None,
                                coinType=coin_type,
                                creator_address=creator_address if creator_address else None
                            )
                            
                            # Small delay between notifications
                            time.sleep(2)
                            
                        except Exception as e:
                            logging.error(f"Error processing token: {e}")
                            continue
                    
                    # Wait before next check
                    logging.info("Waiting 60 seconds before next check...")
                    time.sleep(60)
                    
                except Exception as e:
                    logging.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)
                    continue
                    
        except KeyboardInterrupt:
            logging.info("Token monitoring stopped by user")
        except Exception as e:
            logging.error(f"Fatal error in token monitoring: {e}")
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                logging.info(f"Bot connection successful: {bot_info.get('username', 'Unknown')}")
                return True
            else:
                logging.error(f"Bot connection failed: {result}")
                return False
                
        except Exception as e:
            logging.error(f"Error testing bot connection: {e}")
            return False
    
    def get_chat_info(self) -> Optional[dict]:
        """Get information about the configured chat"""
        try:
            url = f"{self.api_url}/getChat"
            payload = {'chat_id': self.chat_id}
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                chat_info = result.get('result', {})
                logging.info(f"Chat info retrieved: {chat_info.get('title', 'Unknown')}")
                return chat_info
            else:
                logging.error(f"Failed to get chat info: {result}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting chat info: {e}")
            return None

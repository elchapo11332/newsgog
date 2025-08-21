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
        """Get or create monitoring stats"""
        with app.app_context():
            stats = MonitorStats.query.first()
            if not stats:
                stats = MonitorStats()
                db.session.add(stats)
                db.session.commit()
            return stats
    
    def update_stats(self, **kwargs):
        """Update monitoring statistics"""
        with app.app_context():
            stats = self.get_stats()
            for key, value in kwargs.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            db.session.commit()
            
            # Emit stats update via WebSocket
            socketio.emit('stats_update', stats.to_dict())
    
    def is_token_posted(self, contract_address: str) -> bool:
        """Check if a token has already been posted"""
        with app.app_context():
            return PostedToken.query.filter_by(contract_address=contract_address).first() is not None
    
    def save_posted_token(self, name: str, contract_address: str, telegram_message_id: Optional[str] = None):
        """Save a posted token to the database"""
        with app.app_context():
            token = PostedToken(
                name=name,
                contract_address=contract_address,
                telegram_message_id=telegram_message_id
            )
            db.session.add(token)
            db.session.commit()
            
            # Emit new token via WebSocket
            socketio.emit('new_token', token.to_dict())
            
            return token
    
    def fetch_tokens(self):
        """Fetch tokens from the API"""
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Log the raw response for debugging
            logging.debug(f"API Response: {data}")
            
            # The API returns pools instead of tokens
            return data.get("pools", [])
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error fetching tokens: {e}")
            raise
        except Exception as e:
            logging.error(f"Error parsing token data: {e}")
            raise
    
    def process_tokens(self, tokens):
        """Process the fetched tokens and post new ones"""
        new_tokens_count = 0
        posted_tokens_count = 0
        
        for pool in tokens:  # tokens is actually pools now
            try:
                # Extract token name with better fallback logic
                coin_metadata = pool.get("coinMetadata", {})
                
                # Try multiple fields to get the name
                name = (coin_metadata.get("name") or 
                       coin_metadata.get("symbol") or
                       coin_metadata.get("title") or
                       pool.get("name") or
                       pool.get("symbol"))
                
                # Only use "Unknown Token" as final fallback
                if not name or name.strip() == "":
                    name = "Unknown Token"
                else:
                    name = str(name).strip()
                
                # Debug logging for name extraction
                logging.debug(f"Name extraction for {pool.get('coinType', 'NO_COIN_TYPE')[:40]}...")
                logging.debug(f"  coinMetadata: {coin_metadata}")
                logging.debug(f"  extracted name: '{name}'")
                
                # Use coinType as the contract address
                contract = pool.get("coinType")
                
                # Extract pool ID for BUY button
                pool_id = pool.get("coinType")
                
                # Extract creator Twitter handle from metadata (more reliable)
                metadata = pool.get("metadata", {})
                twitter_handle = metadata.get("CreatorTwitterName")
                
                # Extract token image
                token_image = coin_metadata.get("icon_url") or coin_metadata.get("iconUrl")
                
                if not contract:
                    logging.warning(f"Pool missing coinType: {pool}")
                    continue
                
                new_tokens_count += 1
                
                # Check if already posted
                if self.is_token_posted(contract):
                    logging.debug(f"Token already posted: {name} ({contract})")
                    continue
                
                # ONLY post if we have proper token data - prevent "Unknown Token"
                if name == "Unknown Token":
                    logging.warning(f"Skipping token with unknown name: {contract}")
                    continue
                
                # Ensure we have valid token data before posting
                logging.info(f"Found NEW TOKEN to post: {name}")
                logging.info(f"  Contract: {contract}")
                logging.info(f"  Pool ID: {pool_id}")
                logging.info(f"  Twitter: {twitter_handle}")
                logging.info(f"  Has Image: {bool(token_image and token_image.startswith('data:image'))}")
                
                # Create message and BUY button
                message = telegram_bot.format_token_message(name, contract, twitter_handle, pool_id)
                buy_button = telegram_bot.create_buy_button(pool_id) if pool_id else None
                
                if token_image and token_image.startswith('data:image'):
                    # Send as photo with caption and BUY button
                    logging.info(f"Posting {name} as photo with BUY button...")
                    telegram_result = telegram_bot.send_photo(token_image, message, buy_button)
                else:
                    # Send as text message with BUY button
                    logging.info(f"Posting {name} as text message with BUY button...")
                    telegram_result = telegram_bot.send_message(message, buy_button)
                
                if telegram_result:
                    # Save to database with the SAME name we just posted
                    message_id = str(telegram_result.get('message_id', ''))
                    self.save_posted_token(name, contract, message_id)
                    posted_tokens_count += 1
                    
                    logging.info(f"✅ Successfully posted and saved: {name} (Message ID: {message_id})")
                else:
                    logging.error(f"❌ Failed to post token to Telegram: {name}")
                    
            except Exception as e:
                logging.error(f"Error processing pool {pool}: {e}")
                continue
        
        return new_tokens_count, posted_tokens_count
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logging.info("Starting crypto monitoring loop")
        self.running = True
        self.update_stats(is_running=True)
        
        while self.running:
            try:
                logging.debug("Checking for new tokens...")
                
                # Fetch tokens from API
                tokens = self.fetch_tokens()
                
                # Process tokens
                new_count, posted_count = self.process_tokens(tokens)
                
                # Update statistics
                stats = self.get_stats()
                self.update_stats(
                    total_tokens_found=stats.total_tokens_found + new_count,
                    total_tokens_posted=stats.total_tokens_posted + posted_count,
                    last_check=datetime.utcnow(),
                    last_error=None
                )
                
                logging.info(f"Check complete. Found: {new_count}, Posted: {posted_count}")
                
            except Exception as e:
                error_msg = f"Monitor error: {str(e)}"
                logging.error(error_msg)
                self.update_stats(
                    last_check=datetime.utcnow(),
                    last_error=error_msg
                )
                
                # Emit error via WebSocket
                socketio.emit('monitor_error', {'error': error_msg})
            
            # Wait for next check
            time.sleep(self.check_interval)
        
        self.update_stats(is_running=False)
        logging.info("Monitoring loop stopped")
    
    def stop(self):
        """Stop the monitoring loop"""
        self.running = False

# Global monitor instance
monitor = CryptoMonitor()

def start_monitoring():
    """Start the monitoring service"""
    try:
        monitor.monitor_loop()
    except Exception as e:
        logging.error(f"Fatal error in monitoring service: {e}")

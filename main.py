#!/usr/bin/env python3
import logging
import sys
from telegram_bot import TelegramBot

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('telegram_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function to run the Telegram bot"""
    setup_logging()
    
    try:
        # Initialize the bot
        bot = TelegramBot()
        
        # Test connection
        if not bot.test_connection():
            logging.error("Failed to connect to Telegram. Please check your bot token.")
            sys.exit(1)
        
        # Get chat info
        chat_info = bot.get_chat_info()
        if chat_info:
            logging.info(f"Connected to chat: {chat_info.get('title', 'Unknown')}")
        
        # Send test message
        test_result = bot.send_message("🤖 Telegram Bot Started Successfully!")
        if test_result:
            logging.info("Test message sent successfully")
        
        # Start monitoring tokens
        logging.info("Starting token monitoring...")
        bot.monitor_new_tokens()
        
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

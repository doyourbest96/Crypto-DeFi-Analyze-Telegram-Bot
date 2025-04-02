import logging
import sys
from bot.bot import create_bot
from data.database import init_database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # Initialize database connection
    if not init_database():
        logging.error("❌ Could not connect to MongoDB. Please check your configuration.")
        sys.exit(1)
    
    logging.info("🚀 Starting DeFi-Scope Telegram Bot...")
    
    # Create and start the bot
    app = create_bot()
    app.run_polling()

if __name__ == '__main__':
    main()

import logging
import sys
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from handlers.callback_handlers import handle_callback_query as button_callback, handle_expected_input, handle_start_menu, handle_profitable_period_selection, handle_deployer_period_selection
from handlers.error_handlers import error_handler
from data.database import init_database
from services.blockchain import start_blockchain_monitor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

async def post_init(application):
    """Run after the application has been initialized"""
    # Start the blockchain monitor
    await start_blockchain_monitor()

def create_bot():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.Text(["/start"]), handle_start_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expected_input))
    application.add_handler(CallbackQueryHandler(handle_profitable_period_selection, pattern="^profitable_period_"))
    application.add_handler(CallbackQueryHandler(handle_deployer_period_selection, pattern="^deployer_period_"))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    return application

def main():
    # Initialize database connection
    if not init_database():
        logging.error("❌ Could not connect to MongoDB. Please check your configuration.")
        sys.exit(1)
    
    logging.info("🚀 Starting Crypto DeFi Analyze Telegram Bot... 💎")
    
    app = create_bot()
    
    # Start the blockchain monitor in a separate thread
    import threading
    def run_blockchain_monitor():
        asyncio.run(start_blockchain_monitor())
    
    monitor_thread = threading.Thread(target=run_blockchain_monitor)
    monitor_thread.daemon = True  # This ensures the thread will exit when the main program exits
    monitor_thread.start()
    
    # Run the polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

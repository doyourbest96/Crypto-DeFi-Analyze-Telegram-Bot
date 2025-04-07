import logging
import sys

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN

from handlers.callback_handlers import handle_callback_query as button_callback, handle_expected_input, handle_start_menu, handle_profitable_period_selection, handle_deployer_period_selection 
from handlers.error_handlers import error_handler
from data.database import init_database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def create_bot():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.Text(["/start"]), handle_start_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expected_input))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CallbackQueryHandler(handle_profitable_period_selection, pattern="^profitable_period_"))
    application.add_handler(CallbackQueryHandler(handle_deployer_period_selection, pattern="^deployer_period_"))
    application.add_error_handler(error_handler)
        
    return application

def main():
    # Initialize database connection
    if not init_database():
        logging.error("❌ Could not connect to MongoDB. Please check your configuration.")
        sys.exit(1)
    
    logging.info("🚀 Starting DeFi-Scope Telegram Bot... 💎")
    
    app = create_bot()
    app.run_polling()

if __name__ == '__main__':
    main()

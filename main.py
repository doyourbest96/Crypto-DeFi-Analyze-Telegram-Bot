import logging
from bot.bot import create_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # Create and start the bot
    app = create_bot()
    app.run_polling()

if __name__ == '__main__':
    main()

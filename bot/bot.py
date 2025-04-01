from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import TELEGRAM_TOKEN, COMMAND_DESCRIPTIONS
from bot.handlers.command_handlers import (
    start_command, help_command, fb_command, mpw_command, 
    wh_command, ptd_command, kol_command, td_command,
    ath_command, dw_command, th_command, track_command,
    pw_command, hnw_command, premium_command
)
from bot.handlers.callback_handlers import button_callback
from bot.handlers.error_handlers import error_handler

def create_bot():
    # Create the application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("fb", fb_command))
    application.add_handler(CommandHandler("mpw", mpw_command))
    application.add_handler(CommandHandler("wh", wh_command))
    application.add_handler(CommandHandler("ptd", ptd_command))
    application.add_handler(CommandHandler("kol", kol_command))
    application.add_handler(CommandHandler("td", td_command))
    application.add_handler(CommandHandler("ath", ath_command))
    application.add_handler(CommandHandler("dw", dw_command))
    application.add_handler(CommandHandler("th", th_command))
    application.add_handler(CommandHandler("track", track_command))
    application.add_handler(CommandHandler("pw", pw_command))
    application.add_handler(CommandHandler("hnw", hnw_command))
    application.add_handler(CommandHandler("premium", premium_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Set commands for the bot menu
    commands = [
        (command, description) for command, description in COMMAND_DESCRIPTIONS.items()
    ]
    application.bot.set_my_commands(commands)
    
    return application

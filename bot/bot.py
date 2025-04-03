from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN, COMMAND_DESCRIPTIONS
# from bot.handlers.command_handlers import (
#     fb_command, mpw_command, 
#     wh_command, ptd_command, kol_command, td_command,
#     ath_command, dw_command, th_command, track_command,
#     pw_command, hnw_command, premium_command
# )
from bot.handlers.new_command_handlers import general_help_command
from bot.handlers.callback_handlers import handle_callback_query as button_callback, handle_expected_input, handle_start_menu
from bot.handlers.error_handlers import error_handler

def create_bot():
    # Create the application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    # application.add_handler(CommandHandler("help", general_help_command))
    # application.add_handler(CommandHandler("fb", fb_command))
    # application.add_handler(CommandHandler("mpw", mpw_command))
    # application.add_handler(CommandHandler("wh", wh_command))
    # application.add_handler(CommandHandler("ptd", ptd_command))
    # application.add_handler(CommandHandler("kol", kol_command))
    # application.add_handler(CommandHandler("td", td_command))
    # application.add_handler(CommandHandler("ath", ath_command))
    # application.add_handler(CommandHandler("dw", dw_command))
    # application.add_handler(CommandHandler("th", th_command))
    # application.add_handler(CommandHandler("track", track_command))
    # application.add_handler(CommandHandler("pw", pw_command))
    # application.add_handler(CommandHandler("hnw", hnw_command))
    # application.add_handler(CommandHandler("premium", premium_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Text(["/start"]), handle_start_menu))

    # Add message handler for expected inputs (THIS IS THE IMPORTANT PART)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expected_input))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Set commands for the bot menu
    commands = [
        (command, description) for command, description in COMMAND_DESCRIPTIONS.items()
    ]
    application.bot.set_my_commands(commands)
    
    return application

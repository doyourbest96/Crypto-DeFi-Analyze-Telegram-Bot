from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN, COMMAND_DESCRIPTIONS
from bot.handlers import (
    start_command, help_command, fb_command, mpw_command, wh_command,
    ptd_command, kol_command, td_command, ath_command, dw_command,
    th_command, track_command, pw_command, hnw_command, premium_command,
    usage_command, button_callback
)
from bot.middleware import rate_limiter

def create_bot():
    """Create and configure the bot with all handlers"""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add feature command handlers with rate limiting middleware
    application.add_handler(CommandHandler("fb", rate_limiter(fb_command)))
    application.add_handler(CommandHandler("mpw", rate_limiter(mpw_command)))
    application.add_handler(CommandHandler("wh", rate_limiter(wh_command)))
    application.add_handler(CommandHandler("ptd", rate_limiter(ptd_command)))
    application.add_handler(CommandHandler("kol", rate_limiter(kol_command)))
    application.add_handler(CommandHandler("td", rate_limiter(td_command)))
    application.add_handler(CommandHandler("ath", rate_limiter(ath_command)))
    application.add_handler(CommandHandler("dw", rate_limiter(dw_command)))
    application.add_handler(CommandHandler("th", rate_limiter(th_command)))
    application.add_handler(CommandHandler("track", rate_limiter(track_command)))
    application.add_handler(CommandHandler("pw", rate_limiter(pw_command)))
    application.add_handler(CommandHandler("hnw", rate_limiter(hnw_command)))
    
    # Add utility commands
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("usage", usage_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Set bot commands in the menu
    commands = [
        (command, description) for command, description in COMMAND_DESCRIPTIONS.items()
    ]
    application.bot.set_my_commands(commands)
    
    return application

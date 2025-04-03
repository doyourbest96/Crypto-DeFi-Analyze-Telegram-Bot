from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from data.models import User

from src.services.blockchain import * 
from src.services.analytics import *
from src.services.notification import *
from src.services.user_management import *

async def check_user_exists(update: Update) -> User:
    """Check if user exists in database, create if not, and update activity"""
    return await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )

async def check_premium_required(update: Update, context: ContextTypes.DEFAULT_TYPE, feature_name: str) -> bool:
    """Check if a premium feature is being accessed by a non-premium user"""
    user = await check_user_exists(update)
    
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⭐ <b>Premium Feature</b>\n\n"
            f"The {feature_name} feature is only available to premium users.\n\n"
            f"💎 Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return True
    
    return False

async def check_rate_limit(update: Update, scan_type: str, limit: int) -> bool:
    """Check if user has exceeded their daily scan limit"""
    user = await check_user_exists(update)
    user_id = user.user_id
    
    # Use the service function to check rate limit
    has_reached_limit, current_count = await check_rate_limit_service(user_id, scan_type, limit)
    
    if has_reached_limit:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {limit} daily {scan_type} scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Increment scan count using the service function
    await increment_scan_count(user_id, scan_type)
    return 

async def validate_address(update: Update, address: str) -> bool:
    """Validate if the provided string is a valid Ethereum address"""
    if not address or not is_valid_address(address):
        await update.message.reply_text(
            "⚠️ Please provide a valid Ethereum address or token contract address."
        )
        return False
    return True

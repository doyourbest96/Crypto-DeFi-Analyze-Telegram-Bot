from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from data.models import User
from config import SUBSCRIPTION_WALLET_ADDRESS

from services.blockchain import * 
from services.analytics import *
from services.notification import *
from services.user_management import *

async def check_callback_user(update: Update) -> User:
    """Check if user exists in database, create if not, and update activity"""
    return await get_or_create_user(
        user_id=update.callback_query.from_user.id,
        username=update.callback_query.from_user.username,
        first_name=update.callback_query.from_user.first_name,
        last_name=update.callback_query.from_user.last_name
    )

async def check_premium_required(update: Update, context: ContextTypes.DEFAULT_TYPE, feature_name: str) -> bool:
    """Check if a premium feature is being accessed by a non-premium user"""
    user = await check_callback_user(update)
    
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
    user = await check_callback_user(update)
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

async def send_premium_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, plan: str, premium_until: datetime) -> None:
    """Send a welcome message with premium tips to new premium users"""
    welcome_message = (
        f"🎉 <b>Welcome to DeFi-Scope Premium!</b>\n\n"
        f"Hi {user.first_name}, thank you for upgrading to our premium service.\n\n"
        f"<b>Here are some premium features you can now access:</b>\n\n"
        f"• <b>Unlimited Token & Wallet Scans</b>\n"
        f"  Use /scan_token and /scan_wallet as much as you need\n\n"
        f"• <b>Deployer Wallet Analysis</b>\n"
        f"  Use /dw [contract] to analyze token deployers\n\n"
        f"• <b>Top Holders & Whale Tracking</b>\n"
        f"  Use /th [contract] to see top token holders\n\n"
        f"• <b>Wallet & Token Tracking</b>\n"
        f"  Use /track commands to monitor wallets and tokens\n\n"
        f"Need help with premium features? Type /premium_help anytime!\n\n"
        f"Your {plan} subscription is active until: <b>{premium_until.strftime('%d %B %Y')}</b>"
    )
    
    # Send as a new message to avoid replacing the payment confirmation
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_message,
        parse_mode=ParseMode.HTML
    )
    """Handle payment retry callback"""
    query = update.callback_query
    
    # Clear the stored transaction ID
    if "transaction_id" in context.user_data:
        del context.user_data["transaction_id"]
    
    # Set up to collect a new transaction ID
    context.user_data["awaiting_transaction_id"] = True
    context.user_data["premium_plan"] = plan
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 <b>New Transaction ID Required</b>\n\n"
        "Please send the new transaction hash/ID of your payment.\n\n"
        "You can find this in your wallet's transaction history after sending the payment.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

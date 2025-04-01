import functools
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from data.database import get_database
from config import FREE_TOKEN_SCANS_DAILY, FREE_WALLET_SCANS_DAILY

def is_premium_user(user_id):
    """Check if a user has premium status"""
    db = get_database()
    user = db.users.find_one({"user_id": user_id})
    if not user:
        return False
    return user.get("is_premium", False)

def premium_required(func):
    """Decorator to restrict commands to premium users only"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if is_premium_user(user_id):
            return await func(update, context)
        else:
            await update.message.reply_text(
                "⭐ This command is available only for premium users.\n"
                "Use /premium to upgrade your account."
            )
    return wrapper

def rate_limit(scan_type, limit):
    """Decorator to apply rate limiting for free users"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Premium users bypass rate limiting
            if is_premium_user(user_id):
                return await func(update, context)
            
            # Check rate limit for free users
            db = get_database()
            today = datetime.now().date()
            
            # Find user's scans for today
            user_scans = db.user_scans.find_one({
                "user_id": user_id,
                "scan_type": scan_type,
                "date": today.isoformat()
            })
            
            if user_scans and user_scans.get("count", 0) >= limit:
                await update.message.reply_text(
                    f"⚠️ You've reached the daily limit of {limit} {scan_type} scans for free users.\n"
                    "Use /premium to upgrade for unlimited scans."
                )
                return
            
            # Update scan count
            if user_scans:
                db.user_scans.update_one(
                    {"_id": user_scans["_id"]},
                    {"$inc": {"count": 1}}
                )
            else:
                db.user_scans.insert_one({
                    "user_id": user_id,
                    "scan_type": scan_type,
                    "date": today.isoformat(),
                    "count": 1
                })
            
            return await func(update, context)
        return wrapper
    return decorator

# Specific rate limiters
token_scan_limit = rate_limit("token_scan", FREE_TOKEN_SCANS_DAILY)
wallet_scan_limit = rate_limit("wallet_scan", FREE_WALLET_SCANS_DAILY)

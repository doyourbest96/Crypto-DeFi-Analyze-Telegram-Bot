import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import FREE_TOKEN_SCANS_DAILY, FREE_WALLET_SCANS_DAILY, FREE_PROFITABLE_WALLETS_LIMIT
from data.database import ( 
     get_token_data, get_wallet_data, get_profitable_wallets, get_profitable_deployers, get_all_kol_wallets, get_user_tracking_subscriptions
)
from data.models import User
from bot.services.blockchain import * 
from bot.services.analytics import *
from bot.services.notification import *
from bot.services.user_management import *

# Helper functions
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    await check_user_exists(update)
    
    welcome_message = (
        f"""🚀 Welcome to <b>DeFi-Scope Bot</b>, {update.effective_user.first_name}! 🎉\n\n"""
        f"🔎 <b>Your Ultimate DeFi Intelligence Bot!</b>\n"
        f"Stay ahead in the crypto game with powerful analytics, wallet tracking, and market insights. 📊💰\n\n"
        f"✨ <b>What can I do for you?</b>\n\n"
        f"🔥 <b>Token Analysis & Market Insights:</b>\n"
        f"• /fb [contract] - First buyers of a token 🏆\n"
        f"• /mpw [contract] - Most profitable wallets 💸\n"
        f"• /kol [contract] - KOL wallets profitability 🎤\n"
        f"• /ath [contract] - All-time high (ATH) market cap 📈\n\n"
        
        f"🕵️ <b>Wallet & Token Tracking:</b>\n"
        f"• /dw [contract] - Deployer wallet & token history 🏗️ (Premium)\n"
        f"• /th [contract] - Top 10 holders & whale tracking 🐳 (Premium)\n"
        f"• /track [contract] - Monitor whale & dev sales 🔔 (Premium)\n"
        f"• /track wd [wallet] - Track wallet for new token deployments 🚀 (Premium)\n"
        f"• /track wbs [wallet] - Track wallet buys & sells 💼 (Premium)\n\n"
        
        f"💰 <b>High Net Worth & Profitability Scans:</b>\n"
        f"• /pw [trades] [buy amount] [days] [contract] - Profitable wallets 📊 (Premium)\n"
        f"• /hnw [contract] - High net worth wallet holders 💎 (Premium)\n\n"
        
        f"🤖 <b>How to get started?</b>\n"
        f"Simply type a command and let me do the magic! ✨\n"
        f"Need help? Type /help for more details. 🚀\n\n"
        
        f"🔑 <b>Upgrade to Premium for unlimited scans and advanced tracking!</b>\n\n"
        f"Happy Trading! 🚀💰"
    ) 
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 Scan Token", callback_data="scan_token"),
            InlineKeyboardButton("👛 Scan Wallet", callback_data="scan_wallet")
        ],
        [
            InlineKeyboardButton("📈 All-Time High (ATH)", callback_data="ath"),
            InlineKeyboardButton("🐳 Top Holders & Whales", callback_data="top_holders")
        ],
        [
            InlineKeyboardButton("💰 Profitable Wallets", callback_data="profitable_wallets"),
            InlineKeyboardButton("💎 High Net Worth Wallets", callback_data="high_net_worth")
        ],
        [
            InlineKeyboardButton("📊 Track Wallet Buys/Sells", callback_data="track_wallet_trades"),
            InlineKeyboardButton("🚀 Track New Token Deployments", callback_data="track_wallet_deployments")
        ],
        [
            InlineKeyboardButton("🏗️ Deployer Wallet Scan", callback_data="deployer_wallet_scan"),
            InlineKeyboardButton("🔔 Track Whale & Dev Sales", callback_data="track_whale_sales")
        ],
        [
            InlineKeyboardButton("💎 Premium Features", callback_data="premium_info")
        ],
        [
            InlineKeyboardButton("📝 Help", callback_data="general_help"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def general_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    await check_user_exists(update)

    keyboard = [
        [InlineKeyboardButton("📊 Token Analysis", callback_data="token_analysis_help")],
        [InlineKeyboardButton("🕵️ Wallet Scan & Tracking", callback_data="wallet_scan_help")],
        [InlineKeyboardButton("🐳 Whale & Deployer Tracking", callback_data="whale_deployer_help")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    general_help_text = (
        "<b>📌 DeFi-Scope Bot Commands</b>\n\n"
        "I help you <b>analyze tokens, track wallets, and monitor whales</b> in the crypto space.\n\n"
        "Use the buttons below to navigate through the different features.\n\n"
        "📊 Token Analysis – Track first buyers, ATH, and most profitable wallets.\n"
        "🕵️ Wallet Scan & Tracking – Find profitable wallets, check holding durations, and track buy/sell activity.\n"
        "🐳 Whale & Deployer Tracking – See top holders, watch whale movements, and analyze deployer wallets.\n"
        "Tap on any button to explore!\n\n"
    )
    
    await update.message.reply_text(
        general_help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

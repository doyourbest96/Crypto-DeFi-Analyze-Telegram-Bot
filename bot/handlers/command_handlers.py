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
            f"⭐ *Premium Feature*\n\n"
            f"The {feature_name} feature is only available to premium users.\n\n"
            f"💎 Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
    return False


async def validate_address(update: Update, address: str) -> bool:
    """Validate if the provided string is a valid Ethereum address"""
    if not address or not is_valid_address(address):
        await update.message.reply_text(
            "⚠️ Please provide a valid Ethereum address or token contract address."
        )
        return False
    return True

# Command handlers
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
            InlineKeyboardButton("📝 Help", callback_data="help"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    await check_user_exists(update)
    
    help_text = (
        "🔍 <b>DeFi-Scope Bot Commands</b>\n\n"
        "<b>Token Analysis:</b>\n"
        "• /fb <token_address> - First 1-50 buy wallets of a token\n"
        "• /ath <token_address> - All time high market cap of a token\n"
        "• /dw <token_address> - Scan token contract to reveal deployer wallet (Premium)\n"
        "• /th <token_address> - Scan token for top holders (Premium)\n\n"
        
        "<b>Wallet Analysis:</b>\n"
        "• /mpw <token_address> - Most profitable wallets in a token\n"
        "• /wh <wallet_address> <token_address> - How long a wallet holds a token\n"
        "• /td <wallet_address> - Tokens deployed by a wallet (Premium)\n\n"
        
        "<b>Tracking & Monitoring:</b>\n"
        "• /track <type> <address> - Track tokens, wallets or deployments (Premium)\n"
        "• /pw - Profitable wallets in any token (Premium)\n"
        "• /hnw - High net worth wallet holders (Premium)\n\n"
        
        "<b>Special Lists:</b>\n"
        "• /ptd - Most profitable token deployer wallets\n"
        "• /kol - KOL wallets profitability\n\n"
        
        "<b>Other Commands:</b>\n"
        "• /premium - Upgrade to premium\n"
        "• /help - Show this help information"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML
    )

async def fb_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /fb command - First buyers of a token"""
    # Check rate limit for free users
    if await check_rate_limit(update, "token_scan", FREE_TOKEN_SCANS_DAILY):
        return
    
    # Get token address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address.\n"
            "Usage: /fb <token_address>"
        )
        return
    
    token_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing first buyers... This may take a moment."
    )
    
    try:
        # Get first buyers (placeholder - implement actual blockchain query)
        first_buyers = await get_first_buyers(token_address)
        
        if not first_buyers:
            await processing_message.edit_text(
                "❌ Could not find first buyers for this token. It may be too new or not tracked."
            )
            return
        
        # Format the response
        response = f"🔍 <b>First Buyers of {token_address[:6]}...{token_address[-4:]}</b>\n\n"
        
        for i, buyer in enumerate(first_buyers[:10], 1):
            response += (
                f"{i}. `{buyer['address'][:6]}...{buyer['address'][-4:]}`\n"
                f"   Amount: {buyer['amount']} tokens\n"
                f"   Time: {buyer['time']}\n\n"
            )
        
        # Add button to view more
        keyboard = [
            [InlineKeyboardButton("View More Buyers", callback_data=f"more_buyers_{token_address}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in fb_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing first buyers. Please try again later."
        )

async def mpw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mpw command - Most profitable wallets in a token"""
    # Check rate limit for free users
    if await check_rate_limit(update, "token_scan", FREE_TOKEN_SCANS_DAILY):
        return
    
    # Get token address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address.\n"
            "Usage: /mpw <token_address>"
        )
        return
    
    token_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Finding most profitable wallets... This may take a moment."
    )
    
    try:
        # Get profitable wallets (placeholder - implement actual blockchain query)
        user = await check_user_exists(update)
        limit = 10 if user.is_premium else FREE_PROFITABLE_WALLETS_LIMIT
        
        # This would be replaced with actual blockchain data
        profitable_wallets = await get_profitable_wallets(7, limit)
        
        if not profitable_wallets:
            await processing_message.edit_text(
                "❌ Could not find profitable wallets for this token."
            )
            return
        
        # Format the response
        response = f"💰 <b>Most Profitable Wallets for {token_address[:6]}...{token_address[-4:]}</b>\n\n"
        
        for i, wallet in enumerate(profitable_wallets, 1):
            response += (
                f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Profit: ${wallet['win_rate']}%\n"
                f"   Trades: {wallet.get('total_trades', 'N/A')}\n\n"
            )
        
        # Add premium upsell if not premium
        if not user.is_premium:
            response += "\n_Upgrade to premium to see more profitable wallets!_"
            keyboard = [
                [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            keyboard = [
                [InlineKeyboardButton("Export Data", callback_data=f"export_mpw_{token_address}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in mpw_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while finding profitable wallets. Please try again later."
        )

async def wh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /wh command - How long a wallet holds a token"""
    # Check rate limit for free users
    if await check_rate_limit(update, "wallet_scan", FREE_WALLET_SCANS_DAILY):
        return
    
    # Get wallet and token addresses from command arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Please provide both wallet and token addresses.\n"
            "Usage: /wh <wallet_address> <token_address>"
        )
        return
    
    wallet_address = context.args[0]
    token_address = context.args[1]
    
    # Validate addresses
    if not await validate_address(update, wallet_address) or not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing wallet holding time... This may take a moment."
    )
    
    try:
        # Get wallet holding time (placeholder - implement actual blockchain query)
        holding_data = await get_wallet_holding_time(wallet_address, token_address)
        
        if not holding_data:
            await processing_message.edit_text(
                "❌ Could not find holding data for this wallet and token combination."
            )
            return
        
        # Format the response
        response = (
            f"⏱️ <b>Wallet Holding Analysis</b>\n\n"
            f"Wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`\n"
            f"Token: `{token_address[:6]}...{token_address[-4:]}`\n\n"
            f"Average Holding Time: {holding_data.get('avg_holding_time', 'N/A')}\n"
            f"Longest Hold: {holding_data.get('longest_hold', 'N/A')}\n"
            f"Shortest Hold: {holding_data.get('shortest_hold', 'N/A')}\n"
            f"Total Trades: {holding_data.get('total_trades', 'N/A')}\n"
            f"Buy/Sell Ratio: {holding_data.get('buy_sell_ratio', 'N/A')}"
        )
        
        await processing_message.edit_text(
            response,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in wh_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing holding time. Please try again later."
        )

async def ptd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ptd command - Most profitable token deployer wallets"""
    # Check user exists
    await check_user_exists(update)
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Finding most profitable token deployers... This may take a moment."
    )
    
    try:
        # Get profitable deployers (placeholder - implement actual blockchain query)
        user = await check_user_exists(update)
        limit = 10 if user.is_premium else FREE_PROFITABLE_WALLETS_LIMIT
        
        # This would be replaced with actual blockchain data
        profitable_deployers = await get_profitable_deployers(30, limit)
        
        if not profitable_deployers:
            await processing_message.edit_text(
                "❌ Could not find profitable token deployers at this time."
            )
            return
        
        # Format the response
        response = f"🚀 <b>Most Profitable Token Deployers (Last 30 Days)</b>\n\n"
        
        for i, deployer in enumerate(profitable_deployers, 1):
            response += (
                f"{i}. `{deployer['address'][:6]}...{deployer['address'][-4:]}`\n"
                f"   Success Rate: {deployer.get('win_rate', 'N/A')}%\n"
                f"   Tokens Deployed: {deployer.get('tokens_deployed', 'N/A')}\n\n"
            )
        
        # Add premium upsell if not premium
        if not user.is_premium:
            response += "\n_Upgrade to premium to see more profitable deployers!_"
            keyboard = [
                [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            keyboard = [
                [InlineKeyboardButton("Export Data", callback_data="export_ptd")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in ptd_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while finding profitable deployers. Please try again later."
        )

async def kol_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /kol command - KOL wallets profitability"""
    # Check user exists
    await check_user_exists(update)
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing KOL wallets profitability... This may take a moment."
    )
    
    try:
        # Get KOL wallets data
        kol_wallets = await get_all_kol_wallets()
        
        if not kol_wallets:
            await processing_message.edit_text(
                "❌ Could not find KOL wallet data at this time."
            )
            return
        
        # Format the response
        response = f"👑 <b>KOL Wallets Profitability Analysis</b>\n\n"
        
        for i, wallet in enumerate(kol_wallets[:10], 1):
            response += (
                f"{i}. {wallet.get('name', 'Unknown KOL')}\n"
                f"   Wallet: `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
                f"   Profit: ${wallet.get('total_profit', 'N/A')}\n\n"
            )
        
        # Add button to view more
        keyboard = [
            [InlineKeyboardButton("View More KOLs", callback_data="more_kols")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in kol_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing KOL wallets. Please try again later."
        )

async def td_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /td command - Tokens deployed by a wallet (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "Tokens Deployed"):
        return
    
    # Get wallet address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a wallet address.\n"
            "Usage: /td <wallet_address>"
        )
        return
    
    wallet_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, wallet_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Finding tokens deployed by this wallet... This may take a moment."
    )
    
    try:
        # Get tokens deployed by wallet (placeholder - implement actual blockchain query)
        # This would be replaced with actual blockchain data
        wallet_data = await get_wallet_data(wallet_address)
        
        if not wallet_data or not wallet_data.get('deployed_tokens'):
            await processing_message.edit_text(
                "❌ No deployed tokens found for this wallet."
            )
            return
        
        # Format the response
        deployed_tokens = wallet_data.get('deployed_tokens', [])
        response = f"🚀 </b>Tokens Deployed by `{wallet_address[:6]}...{wallet_address[-4:]}`</b>\n\n"
        
        for i, token in enumerate(deployed_tokens[:10], 1):
            response += (
                f"{i}. {token.get('name', 'Unknown Token')} ({token.get('symbol', 'N/A')})\n"
                f"   Address: `{token['address'][:6]}...{token['address'][-4:]}`\n"
                f"   Deployed: {token.get('deploy_date', 'N/A')}\n"
                f"   Success: {token.get('success_rate', 'N/A')}%\n\n"
            )
        
        # Add button to export data
        keyboard = [
            [InlineKeyboardButton("Export Full Data", callback_data=f"export_td_{wallet_address}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in td_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while finding deployed tokens. Please try again later."
        )

async def ath_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ath command - All time high market cap of a token"""
    # Check rate limit for free users
    if await check_rate_limit(update, "token_scan", FREE_TOKEN_SCANS_DAILY):
        return
    
    # Get token address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address.\n"
            "Usage: /ath <token_address>"
        )
        return
    
    token_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing token ATH data... This may take a moment."
    )
    
    try:
        # Get token info (placeholder - implement actual blockchain query)
        token_data = await get_token_data(token_address)
        
        if not token_data:
            await processing_message.edit_text(
                "❌ Could not find data for this token."
            )
            return
        
        # Format the response
        response = (
            f"📈 <b>All-Time High Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
            f"Contract: `{token_address}`\n\n"
            f"ATH Market Cap: ${token_data.get('ath_market_cap', 'N/A')}\n"
            f"ATH Price: ${token_data.get('ath_price', 'N/A')}\n"
            f"ATH Date: {token_data.get('ath_date', 'N/A')}\n\n"
            f"Current Market Cap: ${token_data.get('current_market_cap', 'N/A')}\n"
            f"Current Price: ${token_data.get('current_price', 'N/A')}\n"
            f"% Down From ATH: {token_data.get('ath_drop_percentage', 'N/A')}%"
        )
        
        await processing_message.edit_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )
    
    except Exception as e:
        logging.error(f"Error in ath_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing token ATH. Please try again later."
        )

async def dw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /dw command - Scan token contract to reveal deployer wallet (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "Deployer Wallet Analysis"):
        return
    
    # Get token address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address.\n"
            "Usage: /dw <token_address>"
        )
        return
    
    token_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing token deployer wallet... This may take a moment."
    )
    
    try:
        # Get token info (placeholder - implement actual blockchain query)
        token_data = await get_token_data(token_address)
        
        if not token_data or not token_data.get('deployer_wallet'):
            await processing_message.edit_text(
                "❌ Could not find deployer wallet data for this token."
            )
            return
        
        # Format the response
        deployer = token_data.get('deployer_wallet', {})
        response = (
            f"🔎 <b>Deployer Wallet Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
            f"Deployer Wallet: `{deployer.get('address', 'Unknown')}`\n\n"
            f"Tokens Deployed: {deployer.get('tokens_deployed', 'N/A')}\n"
            f"Success Rate: {deployer.get('success_rate', 'N/A')}%\n"
            f"Avg. ROI: {deployer.get('avg_roi', 'N/A')}%\n"
            f"Rugpull History: {deployer.get('rugpull_count', 'N/A')} tokens\n\n"
            f"Risk Assessment: {deployer.get('risk_level', 'Unknown')}"
        )
        
        # Add button to track this deployer
        keyboard = [
            [InlineKeyboardButton("Track This Deployer", callback_data=f"track_deployer_{deployer.get('address', '')}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in dw_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing deployer wallet. Please try again later."
        )

async def th_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /th command - Scan token for top holders (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "Top Holders Analysis"):
        return
    
    # Get token address from command arguments
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address.\n"
            "Usage: /th <token_address>"
        )
        return
    
    token_address = context.args[0]
    
    # Validate address
    if not await validate_address(update, token_address):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing token top holders... This may take a moment."
    )
    
    try:
        # Get token holders (placeholder - implement actual blockchain query)
        holders = await get_token_holders(token_address)
        token_data = await get_token_data(token_address)
        
        if not holders or not token_data:
            await processing_message.edit_text(
                "❌ Could not find holder data for this token."
            )
            return
        
        # Format the response
        response = (
            f"👥 <b>Top Holders for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        )
        
        for i, holder in enumerate(holders[:10], 1):
            percentage = holder.get('percentage', 'N/A')
            response += (
                f"{i}. `{holder['address'][:6]}...{holder['address'][-4:]}`\n"
                f"   Holdings: {holder.get('amount', 'N/A')} tokens ({percentage}%)\n"
                f"   Value: ${holder.get('value', 'N/A')}\n\n"
            )
        
        # Add button to export data
        keyboard = [
            [InlineKeyboardButton("Export Full Data", callback_data=f"export_th_{token_address}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in th_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing top holders. Please try again later."
        )

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /track command - Track tokens, wallets or deployments (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "Tracking"):
        return
    
    # Get tracking type and address from command arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Please provide tracking type and address.\n"
            "Usage: /track <type> <address>\n\n"
            "Types: token, wallet, deployer"
        )
        return
    
    tracking_type = context.args[0].lower()
    target_address = context.args[1]
    
    # Validate tracking type
    valid_types = ["token", "wallet", "deployer"]
    if tracking_type not in valid_types:
        await update.message.reply_text(
            f"⚠️ Invalid tracking type. Please use one of: {', '.join(valid_types)}"
        )
        return
    
    # Validate address
    if not await validate_address(update, target_address):
        return
    
    # Get user
    user = await check_user_exists(update)
    
    # Get current subscriptions
    current_subscriptions = get_user_tracking_subscriptions(user.user_id)
    
    # Check if already tracking this address/type
    for sub in current_subscriptions:
        if sub.tracking_type == tracking_type and sub.target_address.lower() == target_address.lower():
            await update.message.reply_text(
                f"⚠️ You are already tracking this {tracking_type}."
            )
            return
    
    # Create new tracking subscription
    from data.models import TrackingSubscription
    subscription = TrackingSubscription(
        user_id=user.user_id,
        tracking_type=tracking_type,
        target_address=target_address,
        is_active=True,
        created_at=datetime.now()
    )
    
    # Save subscription
    from data.database import save_tracking_subscription
    save_tracking_subscription(subscription)
    
    # Confirm to user
    await update.message.reply_text(
        f"✅ Now tracking {tracking_type}: `{target_address[:6]}...{target_address[-4:]}`\n\n"
        f"You will receive notifications for significant events related to this {tracking_type}.",
        parse_mode=ParseMode.MARKDOWN
    )

async def pw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /pw command - Profitable wallets in any token (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "Profitable Wallets"):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Finding most profitable wallets across all tokens... This may take a moment."
    )
    
    try:
        # Get profitable wallets (placeholder - implement actual blockchain query)
        # This would be replaced with actual blockchain data
        profitable_wallets = await get_profitable_wallets(30, 20)  # More results for premium users
        
        if not profitable_wallets:
            await processing_message.edit_text(
                "❌ Could not find profitable wallets data at this time."
            )
            return
        
        # Format the response
        response = f"💰 <b>Most Profitable Wallets (Last 30 Days)</b>\n\n"
        
        for i, wallet in enumerate(profitable_wallets[:15], 1):
            response += (
                f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
                f"   Profit: ${wallet.get('total_profit', 'N/A')}\n"
                f"   Trades: {wallet.get('total_trades', 'N/A')}\n\n"
            )
        
        # Add button to export data
        keyboard = [
            [InlineKeyboardButton("Export Full Data", callback_data="export_pw")],
            [InlineKeyboardButton("Track Top Wallets", callback_data="track_top_wallets")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in pw_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while finding profitable wallets. Please try again later."
        )

async def hnw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hnw command - High net worth wallet holders (Premium)"""
    # Check if premium feature is being accessed by non-premium user
    if await check_premium_required(update, context, "High Net Worth Wallets"):
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Finding high net worth wallets... This may take a moment."
    )
    
    try:
        # This would be replaced with actual blockchain data
        # For now, we'll simulate the data
        hnw_wallets = [
            {"address": f"0x{i}abc123def456", "net_worth": i * 1000000, "tokens": i * 5, "active_since": f"20{20-i}"} 
            for i in range(1, 16)
        ]
        
        if not hnw_wallets:
            await processing_message.edit_text(
                "❌ Could not find high net worth wallet data at this time."
            )
            return
        
        # Format the response
        response = f"💎 <b>High Net Worth Wallets</b>\n\n"
        
        for i, wallet in enumerate(hnw_wallets[:10], 1):
            response += (
                f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Net Worth: ${wallet.get('net_worth', 'N/A'):,}\n"
                f"   Tokens Held: {wallet.get('tokens', 'N/A')}\n"
                f"   Active Since: {wallet.get('active_since', 'N/A')}\n\n"
            )
        
        # Add button to export data
        keyboard = [
            [InlineKeyboardButton("Export Full Data", callback_data="export_hnw")],
            [InlineKeyboardButton("Track HNW Wallets", callback_data="track_hnw_wallets")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in hnw_command: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while finding high net worth wallets. Please try again later."
        )

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /premium command - Upgrade to premium"""
    # Check user exists
    user = await check_user_exists(update)
    
    # If user is already premium, show different message
    if user.is_premium:
        premium_until = user.premium_until.strftime("%d %B %Y") if user.premium_until else "Unknown"
        
        await update.message.reply_text(
            f"✨ <b>You're Already a Premium User!</b>\n\n"
            f"Thank you for supporting DeFi-Scope Bot.\n\n"
            f"Your premium subscription is active until: <b>{premium_until}</b>\n\n"
            f"Enjoy all the premium features!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Show premium benefits and pricing
    premium_text = (
        "⭐ <b>Upgrade to DeFi-Scope Premium</b>\n\n"
        "<b>Premium Benefits:</b>\n"
        "• Unlimited token and wallet scans\n"
        "• Access to deployer wallet analysis\n"
        "• Track tokens, wallets, and deployers\n"
        "• View top holders of any token\n"
        "• Access to profitable wallets database\n"
        "• High net worth wallet monitoring\n"
        "• Priority support\n\n"
        
        "<b>Pricing Plans:</b>\n"
        "• Monthly: $19.99/month\n"
        "• Quarterly: $49.99 ($16.66/month)\n"
        "• Annual: $149.99 ($12.50/month)\n\n"
        
        "Select a plan below to upgrade:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("Monthly Plan", callback_data="premium_monthly"),
            InlineKeyboardButton("Quarterly Plan", callback_data="premium_quarterly")
        ],
        [
            InlineKeyboardButton("Annual Plan (Best Value)", callback_data="premium_annual")
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        premium_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

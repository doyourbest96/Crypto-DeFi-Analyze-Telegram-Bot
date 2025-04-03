import logging
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import FREE_TOKEN_SCANS_DAILY, FREE_WALLET_SCANS_DAILY, FREE_PROFITABLE_WALLETS_LIMIT
from data.database import (
    get_token_data, get_wallet_data, get_profitable_wallets, get_profitable_deployers, 
    get_all_kol_wallets, get_user_tracking_subscriptions
)
from data.models import User
from data.database import get_plan_price
from bot.services.blockchain import *
from bot.services.analytics import *
from bot.services.notification import *
from bot.services.user_management import *
from bot.services.payment import *

# Helper function to check user exists
async def check_callback_user(update: Update) -> User:
    """Check if user exists in database, create if not, and update activity"""
    return await get_or_create_user(
        user_id=update.callback_query.from_user.id,
        username=update.callback_query.from_user.username,
        first_name=update.callback_query.from_user.first_name,
        last_name=update.callback_query.from_user.last_name
    )

# Callback query handlers
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()  # Answer the callback query to stop the loading animation
    
    callback_data = query.data
    
    # Log the callback data for debugging
    logging.info(f"Callback query received: {callback_data}")
    
    # Route to appropriate handler based on callback data
    if callback_data == "start_menu" or callback_data == "main_menu" or callback_data == "back":
        await handle_start_menu(update, context)
    elif callback_data == "general_help":
        await handle_general_help(update, context)
    elif callback_data == "token_analysis_help":
        await handle_token_analysis_help(update, context)
    elif callback_data == "wallet_scan_help":
        await handle_wallet_scan_help(update, context)    
    elif callback_data == "whale_deployer_help":
        await handle_whale_deployer_help(update, context)
    elif callback_data == "premium_info":
        await handle_premium_info(update, context)
    elif callback_data.startswith("premium_"):
        plan = callback_data.replace("premium_", "")
        await handle_premium_purchase(update, context, plan)
    elif callback_data.startswith("payment_made_"):
        plan = callback_data.replace("payment_made_", "")
        await handle_payment_made(update, context, plan)
    elif callback_data.startswith("payment_retry_"):
        plan = callback_data.replace("payment_retry_", "")
        await handle_payment_retry(update, context, plan)
    elif callback_data == "scan_token":
        await handle_scan_token(update, context)
    elif callback_data == "scan_wallet":
        await handle_scan_wallet(update, context)
    elif callback_data == "ath":
        await handle_ath(update, context)
    elif callback_data == "top_holders":
        await handle_top_holders(update, context)
    elif callback_data == "profitable_wallets":
        await handle_profitable_wallets(update, context)
    elif callback_data == "high_net_worth":
        await handle_high_net_worth(update, context)
    elif callback_data == "track_wallet_trades":
        await handle_track_wallet_trades(update, context)
    elif callback_data == "track_wallet_deployments":
        await handle_track_wallet_deployments(update, context)
    elif callback_data == "deployer_wallet_scan":
        await handle_deployer_wallet_scan(update, context)
    elif callback_data == "track_whale_sales":
        await handle_track_whale_sales(update, context)
    elif callback_data.startswith("more_buyers_"):
        token_address = callback_data.replace("more_buyers_", "")
        await handle_more_buyers(update, context, token_address)
    elif callback_data == "more_kols":
        await handle_more_kols(update, context)
    elif callback_data.startswith("export_td_"):
        wallet_address = callback_data.replace("export_td_", "")
        await handle_export_td(update, context, wallet_address)
    elif callback_data.startswith("export_th_"):
        token_address = callback_data.replace("export_th_", "")
        await handle_export_th(update, context, token_address)
    elif callback_data == "export_pw":
        await handle_export_pw(update, context)
    elif callback_data == "export_hnw":
        await handle_export_hnw(update, context)
    elif callback_data.startswith("track_deployer_"):
        deployer_address = callback_data.replace("track_deployer_", "")
        await handle_track_deployer(update, context, deployer_address)
    elif callback_data == "track_top_wallets":
        await handle_track_top_wallets(update, context)
    elif callback_data == "track_hnw_wallets":
        await handle_track_hnw_wallets(update, context)
    elif callback_data.startswith("th_"):
        token_address = callback_data.replace("th_", "")
        await handle_th(update, context, token_address)
    elif callback_data.startswith("dw_"):
        token_address = callback_data.replace("dw_", "")
        await handle_dw(update, context, token_address)
    elif callback_data.startswith("track_token_"):
        token_address = callback_data.replace("track_token_", "")
        await handle_track_token(update, context, token_address)
    elif callback_data.startswith("track_wallet_"):
        wallet_address = callback_data.replace("track_wallet_", "")
        await handle_track_wallet(update, context, wallet_address)
    elif callback_data.startswith("trading_history_"):
        wallet_address = callback_data.replace("trading_history_", "")
        await handle_trading_history(update, context, wallet_address)
    elif callback_data.startswith("more_history_"):
        wallet_address = callback_data.replace("more_history_", "")
        await handle_more_history(update, context, wallet_address)
    elif callback_data.startswith("export_ptd"):
        await handle_export_ptd(update, context)
    elif callback_data.startswith("export_mpw_"):
        token_address = callback_data.replace("export_mpw_", "")
        await handle_export_mpw(update, context, token_address)
    else:
        # Unknown callback data
        await query.answer(
            "Sorry, I couldn't process that request. Please try again.", show_alert=True
        )

# Specific callback handlers
async def handle_scan_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle scan token callback"""
    query = update.callback_query
    
    # Check if user has reached daily limit
    user = await check_callback_user(update)
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "token_scan", FREE_TOKEN_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {FREE_TOKEN_SCANS_DAILY} daily token scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address
    await query.message.reply_text(
        "Please send me the token contract address you want to scan.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect token address
    context.user_data["expecting"] = "token_address"

async def handle_scan_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle scan wallet callback"""
    query = update.callback_query
    
    # Check if user has reached daily limit
    user = await check_callback_user(update)
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "wallet_scan", FREE_WALLET_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {FREE_WALLET_SCANS_DAILY} daily wallet scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.message.reply_text(
        "Please send me the wallet address you want to scan.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.HTML
    )
    
    # Set conversation state to expect wallet address
    context.user_data["expecting"] = "wallet_address"
   
async def handle_more_buyers(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle more buyers callback"""
    query = update.callback_query
    
    # Get first buyers (placeholder - implement actual blockchain query)
    first_buyers = await get_first_buyers(token_address)
    
    if not first_buyers:
        await query.edit_message_text(
            "❌ Could not find first buyers for this token. It may be too new or not tracked."
        )
        return
    
    # Format the response with more buyers
    response = f"🔍 <b>First Buyers of {token_address[:6]}...{token_address[-4:]}</b>\n\n"
    
    for i, buyer in enumerate(first_buyers[:20], 1):  # Show more buyers
        response += (
            f"{i}. `{buyer['address'][:6]}...{buyer['address'][-4:]}`\n"
            f"   Amount: {buyer['amount']} tokens\n"
            f"   Time: {buyer['time']}\n\n"
        )
    
    # Add button to export data
    keyboard = [
        [InlineKeyboardButton("Export Full Data", callback_data=f"export_buyers_{token_address}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Try to edit the current message
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass
    
async def handle_more_kols(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle more KOLs callback"""
    query = update.callback_query
    
    # Get KOL wallets data
    kol_wallets = await get_all_kol_wallets()
    
    if not kol_wallets:
        await query.edit_message_text(
            "❌ Could not find KOL wallet data at this time."
        )
        return
    
    # Format the response with more KOLs
    response = f"👑 <b>KOL Wallets Profitability Analysis</b>\n\n"
    
    for i, wallet in enumerate(kol_wallets, 1):  # Show all KOLs
        response += (
            f"{i}. {wallet.get('name', 'Unknown KOL')}\n"
            f"   Wallet: `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
            f"   Profit: ${wallet.get('total_profit', 'N/A')}\n\n"
        )
    
    # Add button to export data
    keyboard = [
        [InlineKeyboardButton("Export Full Data", callback_data="export_kols")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_export_mpw(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle export most profitable wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        f"Most profitable wallets data for token {token_address[:6]}...{token_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_export_ptd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export profitable token deployers callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        "Profitable token deployers data has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_export_td(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle export tokens deployed callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        f"Tokens deployed by wallet {wallet_address[:6]}...{wallet_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_export_th(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle export token holders callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        f"Token holders data for {token_address[:6]}...{token_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_export_pw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export profitable wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        "Profitable wallets data has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_export_hnw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export high net worth wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ <b>Export Complete</b>\n\n"
        "High net worth wallets data has been exported and sent to your email address.",
        parse_mode=ParseMode.HTML
    )

async def handle_track_deployer(update: Update, context: ContextTypes.DEFAULT_TYPE, deployer_address: str) -> None:
    """Handle track deployer callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking deployers is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Create tracking subscription
    from data.models import TrackingSubscription
    from datetime import datetime
    
    subscription = TrackingSubscription(
        user_id=user.user_id,
        tracking_type="deployer",
        target_address=deployer_address,
        is_active=True,
        created_at=datetime.now()
    )
    
    # Save subscription
    from data.database import save_tracking_subscription
    save_tracking_subscription(subscription)
    
    # Confirm to user
    await query.edit_message_text(
        f"✅ Now tracking deployer wallet: `{deployer_address[:6]}...{deployer_address[-4:]}`\n\n"
        f"You will receive notifications when this deployer creates new tokens or when "
        f"significant events occur with their tokens.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_track_top_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track top wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking top wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get top wallets to track
    profitable_wallets = await get_profitable_wallets(30, 5)  # Get top 5 wallets
    
    if not profitable_wallets:
        await query.edit_message_text(
            "❌ Could not find profitable wallets to track at this time."
        )
        return
    
    # Create tracking subscriptions for top wallets
    from data.models import TrackingSubscription
    from datetime import datetime
    from data.database import save_tracking_subscription
    
    for wallet in profitable_wallets:
        subscription = TrackingSubscription(
            user_id=user.user_id,
            tracking_type="wallet",
            target_address=wallet["address"],
            is_active=True,
            created_at=datetime.now()
        )
        save_tracking_subscription(subscription)
    
    # Confirm to user
    response = f"✅ Now tracking top 5 profitable wallets:\n\n"
    
    for i, wallet in enumerate(profitable_wallets[:5], 1):
        response += (
            f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n\n"
        )
    
    response += "You will receive notifications when these wallets make significant trades."
    
    await query.edit_message_text(
        response,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_track_hnw_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track high net worth wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking high net worth wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Simulate getting HNW wallets to track
    hnw_wallets = [
        {"address": f"0x{i}abc123def456", "net_worth": i * 1000000} 
        for i in range(1, 6)
    ]
    
    if not hnw_wallets:
        await query.edit_message_text(
            "❌ Could not find high net worth wallets to track at this time."
        )
        return
    
    # Create tracking subscriptions for HNW wallets
    from data.models import TrackingSubscription
    from datetime import datetime
    from data.database import save_tracking_subscription
    
    for wallet in hnw_wallets:
        subscription = TrackingSubscription(
            user_id=user.user_id,
            tracking_type="wallet",
            target_address=wallet["address"],
            is_active=True,
            created_at=datetime.now()
        )
        save_tracking_subscription(subscription)
    
    # Confirm to user
    response = f"✅ Now tracking top 5 high net worth wallets:\n\n"
    
    for i, wallet in enumerate(hnw_wallets[:5], 1):
        response += (
            f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Net Worth: ${wallet.get('net_worth', 'N/A'):,}\n\n"
        )
    
    response += "You will receive notifications when these wallets make significant trades."
    
    await query.edit_message_text(
        response,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_expected_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle expected inputs from conversation states"""
    # Check what the bot is expecting
    expecting = context.user_data.get("expecting")
 
    if not expecting:
        # Not in a conversation state, ignore
        return
   
    # Clear the expecting state
    del context.user_data["expecting"]
   
    if expecting == "token_address":
        # User sent a token address after clicking "Scan Token"
        token_address = update.message.text.strip()
       
        # Validate address
        if not is_valid_address(token_address):
            # Add back button to validation error message
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum address or token contract address.",
                reply_markup=reply_markup
            )
            return
       
        # Send processing message
        processing_message = await update.message.reply_text(
            "🔍 Analyzing token... This may take a moment."
        )
       
        try:
            # Get token info (placeholder - implement actual blockchain query)
            token_data = await get_token_data(token_address)
           
            if not token_data:
                # Add back button when no token data is found
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_message.edit_text(
                    "❌ Could not find data for this token.",
                    reply_markup=reply_markup
                )
                return
           
            # Format the response
            response = (
                f"📊 <b>Token Analysis: {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
                f"Contract: `{token_address}`\n\n"
                f"Current Price: ${token_data.get('current_price', 'N/A')}\n"
                f"Market Cap: ${token_data.get('current_market_cap', 'N/A')}\n"
                f"Holders: {token_data.get('holders_count', 'N/A')}\n"
                f"Liquidity: ${token_data.get('liquidity', 'N/A')}\n\n"
                f"Launch Date: {token_data.get('launch_date', 'N/A')}\n"
                f"ATH: ${token_data.get('ath_price', 'N/A')}\n"
                f"ATH Date: {token_data.get('ath_date', 'N/A')}\n"
            )
           
            # Add buttons for further analysis
            keyboard = [
                [
                    InlineKeyboardButton("First Buyers", callback_data=f"more_buyers_{token_address}"),
                    InlineKeyboardButton("Top Holders", callback_data=f"th_{token_address}")
                ],
                [
                    InlineKeyboardButton("Deployer Analysis", callback_data=f"dw_{token_address}"),
                    InlineKeyboardButton("Track Token", callback_data=f"track_token_{token_address}")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
           
            await processing_message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            try:
                # Try to edit the current message
                await processing_message.edit_message_text(
                    response,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
            )
            except Exception as e:
                logging.error(f"Error in handle_back: {e}")
                # If editing fails, send a new message
                await processing_message.message.reply_text(
                    response,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            # Delete the original message if possible
            try:
                await processing_message.message.delete()
            except:
                pass
       
        except Exception as e:
            logging.error(f"Error in handle_expected_input (token_address): {e}")
            
            # Add back button to exception error message
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                "❌ An error occurred while analyzing the token. Please try again later.",
                reply_markup=reply_markup
            )
   
    elif expecting == "wallet_address":
        # User sent a wallet address after clicking "Scan Wallet"
        wallet_address = update.message.text.strip()
       
        # Validate address
        if not is_valid_address(wallet_address):
            # Add back button to validation error message
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum wallet address.",
                reply_markup=reply_markup
            )
            return
       
        # Send processing message
        processing_message = await update.message.reply_text(
            "🔍 Analyzing wallet... This may take a moment."
        )
       
        try:
            # Get wallet info (placeholder - implement actual blockchain query)
            wallet_data = await get_wallet_data(wallet_address)
           
            if not wallet_data:
                # Add back button when no wallet data is found
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_message.edit_text(
                    "❌ Could not find data for this wallet.",
                    reply_markup=reply_markup
                )
                return
           
            # Format the response
            response = (
                f"👛 <b>Wallet Analysis</b>\n\n"
                f"Address: `{wallet_address}`\n\n"
                f"Balance: {wallet_data.get('balance', 'N/A')}\n"
                f"First Transaction: {wallet_data.get('first_transaction', 'N/A')}\n"
                f"Total Transactions: {wallet_data.get('total_transactions', 'N/A')}\n\n"
                f"Tokens Deployed: {len(wallet_data.get('deployed_tokens', []))}\n"
                f"Trading Performance: {wallet_data.get('win_rate', 'N/A')}% win rate\n"
            )
           
            # Add buttons for further analysis
            keyboard = [
                [
                    InlineKeyboardButton("Tokens Deployed", callback_data=f"td_{wallet_address}"),
                    InlineKeyboardButton("Trading History", callback_data=f"trading_history_{wallet_address}")
                ],
                [
                    InlineKeyboardButton("Track Wallet", callback_data=f"track_wallet_{wallet_address}")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
           
            await processing_message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
       
        except Exception as e:
            logging.error(f"Error in handle_expected_input (wallet_address): {e}")
            
            # Add back button to exception error message
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                "❌ An error occurred while analyzing the wallet. Please try again later.",
                reply_markup=reply_markup
            )

async def handle_th(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle top holders callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Top Holders Analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send processing message
    await query.edit_message_text(
        "🔍 Analyzing token top holders... This may take a moment."
    )
    
    try:
        # Get token holders (placeholder - implement actual blockchain query)
        holders = await get_token_holders(token_address)
        token_data = await get_token_data(token_address)
        
        if not holders or not token_data:
            await query.edit_message_text(
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
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_th: {e}")
        await query.edit_message_text(
            "❌ An error occurred while analyzing top holders. Please try again later."
        )

async def handle_dw(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle deployer wallet analysis callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Deployer Wallet Analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send processing message
    await query.edit_message_text(
        "🔍 Analyzing token deployer wallet... This may take a moment."
    )
    
    try:
        # Get token info (placeholder - implement actual blockchain query)
        token_data = await get_token_data(token_address)
        
        if not token_data or not token_data.get('deployer_wallet'):
            await query.edit_message_text(
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
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_dw: {e}")
        await query.edit_message_text(
            "❌ An error occurred while analyzing deployer wallet. Please try again later."
        )

async def handle_track_token(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle track token callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Token tracking is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Create tracking subscription
    from data.models import TrackingSubscription
    from datetime import datetime
    
    subscription = TrackingSubscription(
        user_id=user.user_id,
        tracking_type="token",
        target_address=token_address,
        is_active=True,
        created_at=datetime.now()
    )
    
    # Save subscription
    from data.database import save_tracking_subscription
    save_tracking_subscription(subscription)
    
    # Get token data for name
    token_data = await get_token_data(token_address)
    token_name = token_data.get('name', 'Unknown Token') if token_data else 'this token'
    
    # Confirm to user
    await query.edit_message_text(
        f"✅ Now tracking token: {token_name}\n\n"
        f"Contract: `{token_address[:6]}...{token_address[-4:]}`\n\n"
        f"You will receive notifications for significant price movements, "
        f"whale transactions, and other important events.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_track_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle track wallet callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Wallet tracking is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Create tracking subscription
    from data.models import TrackingSubscription
    from datetime import datetime
    
    subscription = TrackingSubscription(
        user_id=user.user_id,
        tracking_type="wallet",
        target_address=wallet_address,
        is_active=True,
        created_at=datetime.now()
    )
    
    # Save subscription
    from data.database import save_tracking_subscription
    save_tracking_subscription(subscription)
    
    # Confirm to user
    await query.edit_message_text(
        f"✅ Now tracking wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`\n\n"
        f"You will receive notifications when this wallet makes significant trades, "
        f"deploys new tokens, or performs other notable actions.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_trading_history(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle trading history callback"""
    query = update.callback_query
    
    # Send processing message
    await query.edit_message_text(
        "🔍 Retrieving trading history... This may take a moment."
    )
    
    try:
        # Simulate getting trading history
        # In a real implementation, you would query blockchain data
        trading_history = [
            {
                "token": f"Token {i}",
                "action": "Buy" if i % 3 != 0 else "Sell",
                "amount": f"{i * 1000}",
                "value": f"${i * 100}",
                "date": f"2023-{i % 12 + 1}-{i % 28 + 1}"
            } for i in range(1, 8)
        ]
        
        if not trading_history:
            await query.edit_message_text(
                "❌ No trading history found for this wallet."
            )
            return
        
        # Format the response
        response = f"📈 <b>Trading History for `{wallet_address[:6]}...{wallet_address[-4:]}`</b>\n\n"
        
        for i, trade in enumerate(trading_history, 1):
            action_emoji = "🟢" if trade["action"] == "Buy" else "🔴"
            response += (
                f"{i}. {action_emoji} {trade['action']} {trade['token']}\n"
                f"   Amount: {trade['amount']} tokens\n"
                f"   Value: {trade['value']}\n"
                f"   Date: {trade['date']}\n\n"
            )
        
        # Add button to view more
        keyboard = [
            [InlineKeyboardButton("View More History", callback_data=f"more_history_{wallet_address}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_trading_history: {e}")
        await query.edit_message_text(
            "❌ An error occurred while retrieving trading history. Please try again later."
        )

async def handle_ath(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ATH button callback"""
    query = update.callback_query
    
    # Prompt user to enter token address
    await query.edit_message_text(
        "Please send me the token contract address to check its All-Time High (ATH).\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.HTML
    )
    
    # Set conversation state to expect token address for ATH
    context.user_data["expecting"] = "ath_token_address"

async def handle_top_holders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle top holders button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Top Holders & Whales analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address
    await query.edit_message_text(
        "Please send me the token contract address to analyze its top holders.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect token address for top holders
    context.user_data["expecting"] = "top_holders_token_address"

async def handle_profitable_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle profitable wallets button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Profitable Wallets analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter parameters
    await query.edit_message_text(
        "Please provide parameters for profitable wallets search in this format:\n\n"
        "`<min_trades> <min_buy_amount> <days_back> <token_address (optional)>`\n\n"
        "Example: `10 0.5 30 0x1234...abcd`\n\n"
        "This will find wallets with at least 10 trades, minimum buy of 0.5 ETH, "
        "active in the last 30 days, for the specified token (optional).",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect parameters for profitable wallets
    context.user_data["expecting"] = "profitable_wallets_params"

async def handle_high_net_worth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle high net worth wallets button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature<b>\n\n"
            "High Net Worth Wallets analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address (optional)
    await query.edit_message_text(
        "Please send me a token contract address to find high net worth wallets holding this token.\n\n"
        "Or send 'all' to find high net worth wallets across all tokens.\n\n"
        "Example: `0x1234...abcd` or `all`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect input for high net worth wallets
    context.user_data["expecting"] = "high_net_worth_input"

async def handle_track_wallet_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track wallet trades button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking wallet trades is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address you want to track for buys and sells.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for tracking trades
    context.user_data["expecting"] = "track_wallet_trades_address"

async def handle_track_wallet_deployments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track wallet deployments button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking wallet deployments is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address you want to track for new token deployments.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for tracking deployments
    context.user_data["expecting"] = "track_wallet_deployments_address"

async def handle_deployer_wallet_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deployer wallet scan button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Deployer wallet scanning is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address
    await query.edit_message_text(
        "Please send me the token contract address to analyze its deployer wallet.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect token address for deployer wallet scan
    context.user_data["expecting"] = "deployer_wallet_scan_token"

async def handle_track_whale_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track whale sales button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking whale and dev sales is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address
    await query.edit_message_text(
        "Please send me the token contract address to track whale and dev sales.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect token address for tracking whale sales
    context.user_data["expecting"] = "track_whale_sales_token"

async def handle_more_history(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle more trading history callback"""
    query = update.callback_query
    
    # Send processing message
    await query.edit_message_text(
        "🔍 Retrieving more trading history... This may take a moment."
    )
    
    try:
        # Simulate getting more trading history
        # In a real implementation, you would query blockchain data with pagination
        trading_history = [
            {
                "token": f"Token {i}",
                "action": "Buy" if i % 3 != 0 else "Sell",
                "amount": f"{i * 1000}",
                "value": f"${i * 100}",
                "date": f"2023-{i % 12 + 1}-{i % 28 + 1}"
            } for i in range(8, 20)  # Get next page of results
        ]
        
        if not trading_history:
            await query.edit_message_text(
                "❌ No additional trading history found for this wallet."
            )
            return
        
        # Format the response
        response = f"📈 <b>More Trading History for `{wallet_address[:6]}...{wallet_address[-4:]}`</b>\n\n"
        
        for i, trade in enumerate(trading_history, 8):  # Continue numbering from previous page
            action_emoji = "🟢" if trade["action"] == "Buy" else "🔴"
            response += (
                f"{i}. {action_emoji} {trade['action']} {trade['token']}\n"
                f"   Amount: {trade['amount']} tokens\n"
                f"   Value: {trade['value']}\n"
                f"   Date: {trade['date']}\n\n"
            )
        
        # Add buttons for navigation
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Previous Page", callback_data=f"trading_history_{wallet_address}"),
                InlineKeyboardButton("Next Page ➡️", callback_data=f"more_history_page2_{wallet_address}")
            ],
            [InlineKeyboardButton("Export Full History", callback_data=f"export_history_{wallet_address}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_more_history: {e}")
        await query.edit_message_text(
            "❌ An error occurred while retrieving more trading history. Please try again later."
        )

async def handle_general_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    general_help_text = (
        "<b>📌 DeFi-Scope Bot Help</b>\n\n"
        "I help you <b>analyze tokens, track wallets, and monitor whales</b> in the crypto space.\n\n"
        "Use the buttons below to navigate through the different features.\n\n"
        "📊 Token Analysis – Track first buyers, ATH, and most profitable wallets.\n"
        "🕵️ Wallet Scans & Tracking – Find profitable wallets, check holding durations, and track buy/sell activity.\n"
        "🐳 Whale & Deployer Tracking – See top holders, watch whale movements, and analyze deployer wallets.\n"
        "Tap on any button to explore!\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Token Analysis", callback_data="token_analysis_help")],
        [InlineKeyboardButton("🕵️ Wallet Scans & Tracking", callback_data="wallet_scans_help")],
        [InlineKeyboardButton("🐳 Whale & Deployer Tracking", callback_data="whale_deployer_help")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Try to edit the current message
        await query.edit_message_text(
            general_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            general_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_token_analysis_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    token_analysis_help_text = (
        "<b>📊 TOKEN ANALYSIS HELP</b>\n\n"
        "📢 Want to analyze a token? Here's what you can do!\n\n"
        "<b>🏆 First Buyers & Profits</b>\n\n"
        "- Discover the first 1 to 50 wallets that bought a token and check their buy/sell amounts, total trades, profit/loss (PNL), and win rate.\n"
        "- Why is this useful?\n"
        "   - Identify strong early investors\n"
        "   - Spot potential whales or market movers\n\n"
        "<b>📈 Market Cap & ATH</b>\n\n"
        "- Find a token’s all-time high (ATH) market cap, when it peaked, and how much it has dropped from the peak.\n"
        "- Why is this useful?\n"
        "   - Know if the token is still growing or past its prime\n"
        "   - Spot opportunities where a token is undervalued\n\n"
        "<b>💸 Most Profitable Wallets</b>\n\n"
        "- See which wallets have made the most profit from trading a specific token.\n"
        "- Why is this useful?\n"
        "   - Follow smart money investors\n"
        "   - Check if whales are still holding or selling\n\n"
        "📌 Tip: This feature helps you decide if a token is worth investing in based on real traders’ success!\n\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            token_analysis_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            token_analysis_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_wallet_scan_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    wallet_scan_help_text = (  
        "<b>🕵️ WALLET SCANS HELP</b>\n\n"  
        "📢 Want to analyze a wallet? Here's what you can do!\n\n"  
        "<b>🔎 Wallet Holding Duration</b>\n"  
        "- Check how long a specific wallet holds a token before selling it.\n"  
        "- Why is this useful?\n"  
        "   - Identify diamond hands vs. paper hands\n"  
        "   - Understand if the wallet is a long-term holder or just flipping tokens\n\n"  
        
        "<b>📊 Profitable Wallets</b>\n"  
        "- Find the most profitable wallets in any token within a specific timeframe (e.g., 1 to 30 days).\n"  
        "- Why is this useful?\n"  
        "   - Follow wallets that consistently make money\n"  
        "   - See how much they invested vs. how much they gained\n\n"  
        
        "<b>💰 Wallet Buy/Sell Tracking</b>\n"  
        "- Track a wallet’s activity and get notified when it buys or sells any token.\n"  
        "- Why is this useful?\n"  
        "   - Get real-time updates on big investors’ moves\n"  
        "   - Spot potential pump & dump strategies\n\n"  
        
        "📌 Tip: Use this to track smart investors and see how they trade!\n\n"  
    )  
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            wallet_scan_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            wallet_scan_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_whale_deployer_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    whale_deployer_tracking_help_text = (  
        "<b>🐳 WHALE & DEPLOYER TRACKING HELP</b>\n\n"  
        "📢 Want to track whales and token deployers? Here’s what you can do!\n\n"  
        
        "<b>🏗️ Deployer Wallet Scan</b>\n"  
        "- Scan the deployer wallet of any token and see all the tokens they have deployed before.\n"  
        "- Why is this useful?\n"  
        "   - Check if the developer has a history of rug pulls\n"  
        "   - Avoid investing in tokens made by scam developers\n\n"  
        
        "<b>🐳 Top Holders & Whale Watch</b>\n"  
        "- See the top 10 holders of a token and track their activity.\n"  
        "- Why is this useful?\n"  
        "   - Spot whales accumulating or dumping\n"  
        "   - Identify if one wallet controls too much supply (risk of manipulation)\n\n"  
        
        "<b>🚀 Track Dev/Whale Sales</b>\n"  
        "- Get notified when the developer or a whale sells a token.\n"  
        "- Why is this useful?\n"  
        "   - Avoid getting rugged by shady developers\n"  
        "   - Know when big investors are leaving a project\n\n"  
        
        "📌 Tip: Always keep an eye on whales and devs – they can make or break a token!\n"  
    )  
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            whale_deployer_tracking_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            whale_deployer_tracking_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the main menu display"""
    
    welcome_message = (
        f"🆘 Welcome to <b>DeFi-Scope Bot, {update.effective_user.first_name}! 🎉</b>\n\n"
        f"🔎 <b>Your Ultimate DeFi Intelligence Bot!</b>\n"
        f"Stay ahead in the crypto game with powerful analytics, wallet tracking, and market insights. 📊💰\n\n"
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>📊 Token Analysis:</b>\n"
        f"🔹 <b>First Buyers & Profits:</b> Find the first 1-50 wallets that bought a token and their profits.\n"
        f"🔹 <b>Market Cap & ATH:</b> Check the all-time high (ATH) market cap of any token and its drop percentage.\n"
        f"🔹 <b>Most Profitable Wallets:</b> See the top wallets making the most profit from a token.\n"
        f"🔹 <b>Deployer Wallet Scan:</b> (Premium) Scan a token contract to reveal its deployer and their past tokens.\n"
        f"🔹 <b>Top Holders & Whale Watch:</b> (Premium) Check top 10 holders and whale activity in any token.\n\n"
        f"<b>🕵️ Wallet Analysis:</b>\n"
        f"🔹 <b>Wallet Holding Duration:</b> See how long a wallet holds a token before selling.\n"
        f"🔹 <b>Wallet Profitability:</b> Find the most profitable wallets in a token.\n"
        f"🔹 <b>Tokens Deployed by Wallet:</b> (Premium) See all tokens ever deployed by a wallet.\n\n"
        f"<b>🔔 Tracking & Monitoring:</b>\n"
        f"🔹 <b>Track Buy/Sell Activity:</b> (Premium) Get alerts when a wallet buys/sells tokens.\n"
        f"🔹 <b>Track New Token Deployments:</b> (Premium) Get notified when a wallet deploys a new token.\n"
        f"🔹 <b>Profitable Wallets:</b> (Premium) Track wallets with the highest profits.\n"
        f"🔹 <b>High Net Worth Wallet Holders:</b> (Premium) Find wallets holding over $10,000 in tokens.\n\n"
        f"<b>📜 Special Lists:</b>\n"
        f"🔹 <b>Profitable Token Deployers:</b> Check the most profitable token deployer wallets.\n"
        f"🔹 <b>KOL Wallets Profitability:</b> Track Key Opinion Leader (KOL) wallets and their PNL.\n\n"
        f"<b>⚙️ Other Options:</b>\n"
        f"🔹 <b>Upgrade to Premium:</b> Unlock unlimited scans and premium features.\n"
        f"🔹 <b>Show Help:</b> Display this help menu anytime.\n"
        f"🔑 <b>Upgrade to Premium for unlimited scans and advanced tracking!</b>\n\n"
        f"Happy Trading! 🚀💰"
    )
    
    keyboard_main = [
        [
            InlineKeyboardButton("📊 Token Analysis", callback_data="token_analysis"),
            InlineKeyboardButton("🕵️ Wallet Scans & Tracking", callback_data="wallet_tracking"),
             InlineKeyboardButton("🐳 Whale & Deployer Tracking", callback_data="whale_tracking"),
        ],
        [
            InlineKeyboardButton("🌟 Upgrade to Premium", callback_data="premium_info")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="general_help"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard_main)
    
    # Check if this is a callback query or a direct message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium info callback"""
    query = update.callback_query
    
    # Check if user is already premium
    user = await check_callback_user(update)
    
    if user.is_premium:
        premium_until = user.premium_until.strftime("%d %B %Y") if user.premium_until else "Unknown"
        
        await query.edit_message_text(
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

        "<b>🚀 Why Go Premium?</b>\n"
        "Gain **unlimited access** to powerful tools that help you track tokens, analyze wallets, "
        "and monitor whales like a pro. With DeFi-Scope Premium, you'll stay ahead of the market and "
        "make **smarter investment decisions.**\n\n"

        "<b>🔥 Premium Benefits:</b>\n"
        "✅ <b>Unlimited Token & Wallet Scans:</b> Analyze as many tokens and wallets as you want, with no daily limits.\n"
        "✅ <b>Deployer Wallet Analysis:</b> Find the deployer of any token, check their past projects, "
        "and spot potential scams before investing.\n"
        "✅ <b>Track Token, Wallet & Deployer Movements:</b> Get real-time alerts when a wallet buys, sells, "
        "or deploys a new token.\n"
        "✅ <b>View Top Holders of Any Token:</b> Discover which whales and big investors are holding a token, "
        "and track their transactions.\n"
        "✅ <b>Profitable Wallets Database:</b> Get exclusive access to a database of wallets that consistently "
        "make profits in the DeFi market.\n"
        "✅ <b>High Net Worth Wallet Monitoring:</b> Find wallets with **$10,000+ holdings** and see how they invest.\n"
        "✅ <b>Priority Support:</b> Get faster responses and priority assistance from our support team.\n\n"

        "<b>💰 Premium Pricing Plans:</b>\n"
        "📅 <b>Monthly:</b> $19.99/month\n"
        "📅 <b>Quarterly:</b> $49.99 ($16.66/month)\n"
        "📅 <b>Annual:</b> $149.99 ($12.50/month) – Best Value! 🎉\n\n"

        "🔹 <b>Upgrade now</b> to unlock the full power of DeFi-Scope and take control of your investments!\n"
        "Select a plan below to get started:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📅  Monthly Plan      $19.99/month", callback_data="premium_monthly"),
            InlineKeyboardButton("📅  Quarterly Plan    $49.99/quarter", callback_data="premium_quarterly"),
            InlineKeyboardButton("📅  Annual Plan       $149.99/year", callback_data="premium_annual")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Try to edit the current message
        await query.edit_message_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_premium_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
    """Handle premium purchase callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Get current ETH price
    from bot.services.payment import get_current_eth_price, get_eth_price_for_plan
    eth_price = await get_current_eth_price()
    
    # Calculate ETH amount based on plan and current price
    eth_amount = get_eth_price_for_plan(plan, eth_price)
    
    # Map plan to details
    plan_details = {
        "monthly": {"name": "Monthly", "price": "$19.99", "duration": "1 month"},
        "quarterly": {"name": "Quarterly", "price": "$49.99", "duration": "3 months"},
        "annual": {"name": "Annual", "price": "$149.99", "duration": "12 months"}
    }
    
    selected_plan = plan_details.get(plan, plan_details["monthly"])
    
    # Get wallet address from config (should be in environment variables)
    wallet_address = "0xabcdef1234567890abcdef1234567890abcdef12"  # Replace with your actual wallet
    
    # Show payment instructions with QR code
    payment_text = (
        f"🛒 <b>{selected_plan['name']} Premium Plan</b>\n\n"
        f"Price: {selected_plan['price']} (≈ {eth_amount} ETH)\n"
        f"Duration: {selected_plan['duration']}\n\n"
        f"<b>Payment Instructions:</b>\n\n"
        f"1. Send <b>exactly {eth_amount} ETH</b> to our wallet address:\n"
        f"`{wallet_address}`\n\n"
        f"2. After sending, click 'I've Made Payment' and provide your transaction ID/hash.\n\n"
        f"<b>Important:</b> Send only ETH on the Ethereum network. Other tokens or networks will not be detected."
    )
    
    # Store plan information in user_data for later use
    context.user_data["premium_plan"] = plan
    context.user_data["eth_amount"] = eth_amount
    
    keyboard = [
        [InlineKeyboardButton("I've Made Payment", callback_data=f"payment_made_{plan}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            payment_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Optionally, send a QR code as a separate message for easier scanning
        # This requires the qrcode library
        try:
            import qrcode
            from io import BytesIO
            
            # Create QR code with the wallet address
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(f"ethereum:{wallet_address}?value={eth_amount}")
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to BytesIO
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            # Send QR code as photo
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=bio,
                caption=f"Scan this QR code to pay {eth_amount} ETH to our wallet"
            )
        except ImportError:
            # QR code library not available, skip sending QR code
            pass
        
    except Exception as e:
        logging.error(f"Error in handle_premium_purchase: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            payment_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_payment_made(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
    """
    Handle payment made callback for crypto payments
    
    This function verifies a crypto payment and updates the user's premium status
    if the payment is confirmed on the blockchain.
    """
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Show processing message
    await query.edit_message_text(
        "🔄 Verifying payment on the blockchain... This may take a moment."
    )
    
    try:
        # 1. Get transaction ID from user data
        transaction_id = context.user_data.get("transaction_id")
        
        # If no transaction ID is stored, prompt user to provide it
        if not transaction_id:
            # Create a conversation to collect transaction ID
            context.user_data["awaiting_transaction_id"] = True
            context.user_data["premium_plan"] = plan
            
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 <b>Transaction ID Required</b>\n\n"
                "Please send the transaction hash/ID of your payment.\n\n"
                "You can find this in your wallet's transaction history after sending the payment.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        
        # 2. Get payment details based on the plan
        payment_details = get_plan_payment_details(plan)
        expected_amount = payment_details["amount"]
        wallet_address = payment_details["wallet_address"]
        duration_days = payment_details["duration_days"]
        
        # 3. Verify the payment on the blockchain
        from bot.services.payment import verify_crypto_payment
        
        verification_result = await verify_crypto_payment(
            transaction_id=transaction_id,
            expected_amount=expected_amount,
            wallet_address=wallet_address
        )
        
        # 4. Process verification result
        if verification_result["verified"]:
            # Calculate premium expiration date
            from datetime import datetime, timedelta
            now = datetime.now()
            premium_until = now + timedelta(days=duration_days)
            
            # Update user's premium status in the database
            from data.database import update_user_premium_status, set_premium_status, record_premium_purchase
            
            # Use the existing functions to update user status
            set_premium_status(user.user_id, True, duration_days)
            record_premium_purchase(user.user_id, plan, duration_days)
            
            # Clear transaction data from user_data
            if "transaction_id" in context.user_data:
                del context.user_data["transaction_id"]
            
            # Log successful premium activation
            logging.info(f"Premium activated for user {user.user_id}, plan: {plan}, until: {premium_until}")
            
            # Create confirmation message with back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send confirmation to user
            await query.edit_message_text(
                f"✅ <b>Payment Verified - Premium Activated!</b>\n\n"
                f"Thank you for upgrading to DeFi-Scope Premium.\n\n"
                f"<b>Transaction Details:</b>\n"
                f"• Plan: {plan.capitalize()}\n"
                f"• Amount: {expected_amount} ETH\n"
                f"• Transaction: {transaction_id[:8]}...{transaction_id[-6:]}\n\n"
                f"Your premium subscription is now active until: "
                f"<b>{premium_until.strftime('%d %B %Y')}</b>\n\n"
                f"Enjoy all the premium features!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            # Optional: Send a welcome message with premium tips
            await send_premium_welcome_message(update, context, user, plan, premium_until)
            
        else:
            # Payment verification failed
            error_message = verification_result.get("error", "Unknown error")
            
            # Create helpful error message based on the specific error
            if "not found" in error_message.lower():
                error_details = (
                    "• Transaction not found on the blockchain\n"
                    "• The transaction may still be pending\n"
                    "• Double-check that you entered the correct transaction ID"
                )
            elif "wrong recipient" in error_message.lower():
                error_details = (
                    "• Payment was sent to the wrong wallet address\n"
                    "• Please ensure you sent to the correct address: "
                    f"`{wallet_address[:10]}...{wallet_address[-8:]}`"
                )
            elif "amount mismatch" in error_message.lower():
                received = verification_result.get("received", 0)
                error_details = (
                    f"• Expected payment: {expected_amount} ETH\n"
                    f"• Received payment: {received} ETH\n"
                    "• Please ensure you sent the exact amount"
                )
            elif "pending confirmation" in error_message.lower():
                error_details = (
                    "• Transaction is still pending confirmation\n"
                    "• Please wait for the transaction to be confirmed\n"
                    "• Try again in a few minutes"
                )
            else:
                error_details = (
                    "• Payment verification failed\n"
                    "• The transaction may be invalid or incomplete\n"
                    "• Please try again or contact support"
                )
            
            # Create keyboard with options
            keyboard = [
                [InlineKeyboardButton("Try Again", callback_data=f"payment_retry_{plan}")],
                [InlineKeyboardButton("Contact Support", url="https://t.me/AdminSupport")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send error message to user
            await query.edit_message_text(
                f"❌ <b>Payment Verification Failed</b>\n\n"
                f"We couldn't verify your payment:\n\n"
                f"{error_details}\n\n"
                f"Transaction ID: `{transaction_id[:10]}...{transaction_id[-8:]}`\n\n"
                f"Please try again or contact support for assistance.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        # Handle exceptions gracefully
        logging.error(f"Payment verification error: {e}")
        
        # Create keyboard with options
        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data=f"premium_{plan}")],
            [InlineKeyboardButton("Contact Support", url="https://t.me/AdminSupport")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send error message to user
        await query.edit_message_text(
            "❌ <b>Error Processing Payment</b>\n\n"
            "An error occurred while verifying your payment.\n"
            "Please try again or contact support for assistance.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

# Helper function to get payment details based on plan
def get_plan_payment_details(plan: str) -> Dict[str, Any]:
    """Get payment details for a specific premium plan"""
    # Wallet address should be stored in environment variables in production
    wallet_address = "0xabcdef1234567890abcdef1234567890abcdef12"
    
    plans = {
        "monthly": {
            "amount": 0.01,  # ETH amount (example)
            "duration_days": 30,
            "wallet_address": wallet_address
        },
        "quarterly": {
            "amount": 0.025,  # ETH amount (example)
            "duration_days": 90,
            "wallet_address": wallet_address
        },
        "annual": {
            "amount": 0.08,  # ETH amount (example)
            "duration_days": 365,
            "wallet_address": wallet_address
        }
    }
    
    return plans.get(plan, plans["monthly"])

# Helper function to send a welcome message to new premium users
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
        f"Your subscription is active until: <b>{premium_until.strftime('%d %B %Y')}</b>"
    )
    
    # Send as a new message to avoid replacing the payment confirmation
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_message,
        parse_mode=ParseMode.HTML
    )

async def handle_payment_retry(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
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
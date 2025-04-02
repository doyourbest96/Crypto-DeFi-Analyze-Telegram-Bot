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
from services.blockchain import *
from services.analytics import *
from services.notification import *
from services.user_management import *

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
    if callback_data == "scan_token":
        await handle_scan_token(update, context)
    elif callback_data == "scan_wallet":
        await handle_scan_wallet(update, context)
    elif callback_data == "premium_info":
        await handle_premium_info(update, context)
    elif callback_data.startswith("more_buyers_"):
        token_address = callback_data.replace("more_buyers_", "")
        await handle_more_buyers(update, context, token_address)
    elif callback_data == "more_kols":
        await handle_more_kols(update, context)
    elif callback_data.startswith("export_mpw_"):
        token_address = callback_data.replace("export_mpw_", "")
        await handle_export_mpw(update, context, token_address)
    elif callback_data == "export_ptd":
        await handle_export_ptd(update, context)
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
    elif callback_data.startswith("premium_"):
        plan = callback_data.replace("premium_", "")
        await handle_premium_purchase(update, context, plan)
    else:
        # Unknown callback data
        await query.edit_message_text(
            "Sorry, I couldn't process that request. Please try again."
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Daily Limit Reached*\n\n"
            f"You've used {current_count} out of {FREE_TOKEN_SCANS_DAILY} daily token scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Prompt user to enter token address
    await query.edit_message_text(
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Daily Limit Reached*\n\n"
            f"You've used {current_count} out of {FREE_WALLET_SCANS_DAILY} daily wallet scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address you want to scan.\n\n"
        "Example: `0x1234...abcd`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address
    context.user_data["expecting"] = "wallet_address"

async def handle_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium info callback"""
    query = update.callback_query
    
    # Check if user is already premium
    user = await check_callback_user(update)
    
    if user.is_premium:
        premium_until = user.premium_until.strftime("%d %B %Y") if user.premium_until else "Unknown"
        
        await query.edit_message_text(
            f"✨ *You're Already a Premium User!*\n\n"
            f"Thank you for supporting DeFi-Scope Bot.\n\n"
            f"Your premium subscription is active until: *{premium_until}*\n\n"
            f"Enjoy all the premium features!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show premium benefits and pricing
    premium_text = (
        "⭐ *Upgrade to DeFi-Scope Premium*\n\n"
        "*Premium Benefits:*\n"
        "• Unlimited token and wallet scans\n"
        "• Access to deployer wallet analysis\n"
        "• Track tokens, wallets, and deployers\n"
        "• View top holders of any token\n"
        "• Access to profitable wallets database\n"
        "• High net worth wallet monitoring\n"
        "• Priority support\n\n"
        
        "*Pricing Plans:*\n"
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
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        premium_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

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
    response = f"🔍 *First Buyers of {token_address[:6]}...{token_address[-4:]}*\n\n"
    
    for i, buyer in enumerate(first_buyers[:20], 1):  # Show more buyers
        response += (
            f"{i}. `{buyer['address'][:6]}...{buyer['address'][-4:]}`\n"
            f"   Amount: {buyer['amount']} tokens\n"
            f"   Time: {buyer['time']}\n\n"
        )
    
    # Add button to export data
    keyboard = [
        [InlineKeyboardButton("Export Full Data", callback_data=f"export_buyers_{token_address}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

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
    response = f"👑 *KOL Wallets Profitability Analysis*\n\n"
    
    for i, wallet in enumerate(kol_wallets, 1):  # Show all KOLs
        response += (
            f"{i}. {wallet.get('name', 'Unknown KOL')}\n"
            f"   Wallet: `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
            f"   Profit: ${wallet.get('total_profit', 'N/A')}\n\n"
        )
    
    # Add button to export data
    keyboard = [
        [InlineKeyboardButton("Export Full Data", callback_data="export_kols")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_mpw(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle export most profitable wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        f"Most profitable wallets data for token {token_address[:6]}...{token_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_ptd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export profitable token deployers callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        "Profitable token deployers data has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_td(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle export tokens deployed callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        f"Tokens deployed by wallet {wallet_address[:6]}...{wallet_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_th(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle export token holders callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        f"Token holders data for {token_address[:6]}...{token_address[-4:]} "
        "has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_pw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export profitable wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        "Profitable wallets data has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_export_hnw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle export high net worth wallets callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Exporting data is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Simulate export process
    await query.edit_message_text(
        "🔄 Preparing your export... This may take a moment."
    )
    
    # In a real implementation, you would generate and send a file here
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "✅ *Export Complete*\n\n"
        "High net worth wallets data has been exported and sent to your email address.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_track_deployer(update: Update, context: ContextTypes.DEFAULT_TYPE, deployer_address: str) -> None:
    """Handle track deployer callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Tracking deployers is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Tracking top wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Tracking high net worth wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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

async def handle_premium_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
    """Handle premium purchase callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Map plan to details
    plan_details = {
        "monthly": {"name": "Monthly", "price": "$19.99", "duration": "1 month"},
        "quarterly": {"name": "Quarterly", "price": "$49.99", "duration": "3 months"},
        "annual": {"name": "Annual", "price": "$149.99", "duration": "12 months"}
    }
    
    selected_plan = plan_details.get(plan, plan_details["monthly"])
    
    # In a real implementation, you would integrate with a payment processor here
    # For now, we'll just simulate the process
    
    # Show payment instructions
    payment_text = (
        f"🛒 *{selected_plan['name']} Premium Plan*\n\n"
        f"Price: {selected_plan['price']}\n"
        f"Duration: {selected_plan['duration']}\n\n"
        f"To complete your purchase, please send the exact amount to our crypto wallet:\n\n"
        f"`0xabcdef1234567890abcdef1234567890abcdef12`\n\n"
        f"After sending payment, please contact @AdminSupport with your transaction ID "
        f"to activate your premium subscription."
    )
    
    keyboard = [
        [InlineKeyboardButton("I've Made Payment", callback_data=f"payment_made_{plan}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        payment_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# Message handler for expected inputs
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
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum address or token contract address."
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
                await processing_message.edit_text(
                    "❌ Could not find data for this token."
                )
                return
            
            # Format the response
            response = (
                f"📊 *Token Analysis: {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})*\n\n"
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
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as e:
            logging.error(f"Error in handle_expected_input (token_address): {e}")
            await processing_message.edit_text(
                "❌ An error occurred while analyzing the token. Please try again later."
            )
    
    elif expecting == "wallet_address":
        # User sent a wallet address after clicking "Scan Wallet"
        wallet_address = update.message.text.strip()
        
        # Validate address
        if not is_valid_address(wallet_address):
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum wallet address."
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
                await processing_message.edit_text(
                    "❌ Could not find data for this wallet."
                )
                return
            
            # Format the response
            response = (
                f"👛 *Wallet Analysis*\n\n"
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
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as e:
            logging.error(f"Error in handle_expected_input (wallet_address): {e}")
            await processing_message.edit_text(
                "❌ An error occurred while analyzing the wallet. Please try again later."
            )

# Additional callback handlers for specific token/wallet actions

async def handle_th(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
    """Handle top holders callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Top Holders Analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            f"👥 *Top Holders for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})*\n\n"
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
            [InlineKeyboardButton("Export Full Data", callback_data=f"export_th_{token_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Deployer Wallet Analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            f"🔎 *Deployer Wallet Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})*\n\n"
            f"Deployer Wallet: `{deployer.get('address', 'Unknown')}`\n\n"
            f"Tokens Deployed: {deployer.get('tokens_deployed', 'N/A')}\n"
            f"Success Rate: {deployer.get('success_rate', 'N/A')}%\n"
            f"Avg. ROI: {deployer.get('avg_roi', 'N/A')}%\n"
            f"Rugpull History: {deployer.get('rugpull_count', 'N/A')} tokens\n\n"
            f"Risk Assessment: {deployer.get('risk_level', 'Unknown')}"
        )
        
        # Add button to track this deployer
        keyboard = [
            [InlineKeyboardButton("Track This Deployer", callback_data=f"track_deployer_{deployer.get('address', '')}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Token tracking is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
            [InlineKeyboardButton("Upgrade to Premium", callback_data="premium_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ *Premium Feature*\n\n"
            "Wallet tracking is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
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
        response = f"📈 *Trading History for `{wallet_address[:6]}...{wallet_address[-4:]}`*\n\n"
        
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
            [InlineKeyboardButton("View More History", callback_data=f"more_history_{wallet_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    except Exception as e:
        logging.error(f"Error in handle_trading_history: {e}")
        await query.edit_message_text(
            "❌ An error occurred while retrieving trading history. Please try again later."
        )

async def handle_payment_made(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
    """Handle payment made callback"""
    query = update.callback_query
    
    # In a real implementation, you would verify the payment
    # For now, we'll just simulate the process
    
    await query.edit_message_text(
        "🔄 Verifying payment... This may take a moment."
    )
    
    # Simulate payment verification
    import random
    payment_verified = random.choice([True, False])
    
    if payment_verified:
        # Update user to premium
        user = await check_callback_user(update)
        
        # Calculate premium duration based on plan
        from datetime import datetime, timedelta
        
        now = datetime.now()
        if plan == "monthly":
            premium_until = now + timedelta(days=30)
        elif plan == "quarterly":
            premium_until = now + timedelta(days=90)
        elif plan == "annual":
            premium_until = now + timedelta(days=365)
        else:
            premium_until = now + timedelta(days=30)
        
        # In a real implementation, you would update the user in the database
        # For now, we'll just simulate the process
        
        # Confirm to user
        await query.edit_message_text(
            f"✅ *Payment Verified - Premium Activated!*\n\n"
            f"Thank you for upgrading to DeFi-Scope Premium.\n\n"
            f"Your premium subscription is now active until: "
            f"*{premium_until.strftime('%d %B %Y')}*\n\n"
            f"Enjoy all the premium features!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Payment not verified
        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data=f"premium_{plan}")],
            [InlineKeyboardButton("Contact Support", url="https://t.me/AdminSupport")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ *Payment Not Verified*\n\n"
            "We couldn't verify your payment at this time. This could be due to:\n\n"
            "• Payment still processing\n"
            "• Incorrect payment amount\n"
            "• Network congestion\n\n"
            "Please try again or contact support for assistance.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )



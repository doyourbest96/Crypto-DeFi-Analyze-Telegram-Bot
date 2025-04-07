import logging
from typing import Dict, Any
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import FREE_TOKEN_SCANS_DAILY, FREE_RESPONSE_DAILY, FREE_WALLET_SCANS_DAILY, PREMIUM_RESPONSE_DAILY
from data.database import (
    get_wallet_data, get_profitable_wallets, get_profitable_deployers, 
    get_all_kol_wallets, get_user_tracking_subscriptions, get_user
)
from data.models import User, TrackingSubscription
from data.database import *

from services.blockchain import *
from services.analytics import *
from services.notification import *
from services.user_management import *
from services.payment import *

from utils import *

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()  # Answer the callback query to stop the loading animation
    
    callback_data = query.data
    
    # Log the callback data for debugging
    logging.info(f"Callback query received: {callback_data}")
    
    # Route to appropriate handler based on callback data
    if callback_data == "start_menu" or callback_data == "main_menu":
        await handle_start_menu(update, context)
    elif callback_data == "back":
        current_text = query.message.text or query.message.caption or ""
        if "Welcome to DeFi-Scope Bot" in current_text and "Your Ultimate DeFi Intelligence Bot" in current_text:
            await query.answer("You're already at the main menu")
        else:
            await handle_start_menu(update, context)
    elif callback_data == "select_network":
        await handle_select_network(update, context)
    elif callback_data.startswith("set_default_network_"):
        await handle_set_default_network(update, context)
    elif callback_data == "token_analysis":
        await handle_token_analysis(update, context)
    elif callback_data == "wallet_analysis":
        await handle_wallet_analysis(update, context)
    elif callback_data == "tracking_and_monitoring":
        await handle_tracking_and_monitoring(update, context)
    elif callback_data == "kol_wallets":
        await handle_kol_wallets(update, context)
    elif callback_data == "token_first_buyers":
        await handle_first_buyers(update, context)
    elif callback_data == "token_most_profitable_wallets":
        await handle_token_most_profitable_wallets(update, context)
    elif callback_data == "token_ath":
        await handle_ath(update, context)
    elif callback_data == "token_deployer_wallet_scan":
        await handle_deployer_wallet_scan(update, context)
    elif callback_data == "token_top_holders":
        await handle_top_holders(update, context)
    elif callback_data == "token_high_net_worth_holders":
        await handle_high_net_worth_holders(update, context)
    elif callback_data == "wallet_most_profitable_in_period":
        await handle_wallet_most_profitable_in_period(update, context)
    elif callback_data == "wallet_holding_duration":
        await handle_wallet_holding_duration(update, context)
    elif callback_data == "most_profitable_token_deployer_wallet":
        await handle_most_profitable_token_deployer_wallet(update, context)
    elif callback_data == "tokens_deployed_by_wallet":
        await handle_tokens_deployed_by_wallet(update, context)
    elif callback_data == "track_wallet_buy_sell":
        await handle_track_wallet_buy_sell(update, context)
    elif callback_data == "track_new_token_deploy":
        await handle_track_new_token_deploy(update, context)
    elif callback_data == "track_profitable_wallets":
        await handle_track_profitable_wallets(update, context)
    elif callback_data == "kol_wallet_profitability":
        await handle_kol_wallet_profitability(update, context)
    elif callback_data == "track_whale_wallets":
        await handle_track_whale_wallets(update, context)
    elif "_chain_" in callback_data:
        await handle_chain_selection_callback(update, context)

    

    


    
    


    elif callback_data == "general_help":
        await handle_general_help(update, context)
    elif callback_data == "token_analysis_help":
        await handle_token_analysis_help(update, context)
    elif callback_data == "wallet_analysis_help":
        await handle_wallet_analysis_help(update, context)    
    elif callback_data == "tracking_and_monitoring_help":
        await handle_tracking_and_monitoring_help(update, context)
    elif callback_data == "kol_wallets_help":
        await handle_kol_wallets_help(update, context)
    elif callback_data == "premium_info":
        await handle_premium_info(update, context)
    elif callback_data.startswith("premium_plan_"):
        parts = callback_data.replace("premium_plan_", "").split("_")
        if len(parts) == 2:
            plan, currency = parts
            await handle_premium_purchase(update, context, plan, currency)
        else:
            await query.answer("Invalid plan selection", show_alert=True)
    elif callback_data.startswith("payment_made_"):
        parts = callback_data.replace("payment_made_", "").split("_")
        if len(parts) == 2:
            plan, currency = parts
            await handle_payment_made(update, context, plan, currency)
        else:
            await query.answer("Invalid payment confirmation", show_alert=True)
        


    elif callback_data == "track_wallet_trades":
        await handle_track_wallet_trades(update, context)
    elif callback_data == "track_wallet_deployments":
        await handle_track_wallet_deployments(update, context)
    elif callback_data == "track_whale_sales":
        await handle_track_whale_sales(update, context)
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
    # elif callback_data.startswith("th_"):
    #     token_address = callback_data.replace("th_", "")
    #     await handle_th(update, context, token_address)
    # elif callback_data.startswith("dw_"):
    #     token_address = callback_data.replace("dw_", "")
    #     await handle_dw(update, context, token_address)
    # elif callback_data.startswith("track_token_"):
    #     token_address = callback_data.replace("track_token_", "")
    #     await handle_track_token(update, context, token_address)
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
        await query.answer(
            "Sorry, I couldn't process that request. Please try again.", show_alert=True
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Exporting data is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking deployers is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking top wallets is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking high net worth wallets is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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

    if expecting == "first_buyers_token_address":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="first_buyers",
            get_data_func=get_token_first_buyers,
            format_response_func=format_first_buyers_response,
            scan_count_type="first_buy_wallet_scan",
            processing_message_text="🔍 Analyzing token's first buyers... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the token's first buyers. Please try again later.",
            no_data_message_text="❌ Could not find first buyers data for this token."
        )
        
    elif expecting == "token_most_profitable_wallets_token_address":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="most_profitable_wallets",
            get_data_func=get_token_profitable_wallets,
            format_response_func=format_profitable_wallets_response,
            scan_count_type="token_most_profitable_wallet_scan",
            processing_message_text="🔍 Analyzing most profitable wallets for this token... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the token's most profitable wallets. Please try again later.",
            no_data_message_text="❌ Could not find profitable wallets data for this token."
        )
    
    elif expecting == "ath_token_address":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="ath",
            get_data_func=get_ath_data,
            format_response_func=format_ath_response,
            scan_count_type="ath_scan",
            processing_message_text="🔍 Analyzing token's ATH data... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the token's ATH data. Please try again later.",
            no_data_message_text="❌ Could not find ATH data for this token."
        )

    elif expecting == "deployer_wallet_scan_token":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="deployer_wallet_scan",
            get_data_func=get_deployer_wallet_scan_data,
            format_response_func=format_deployer_wallet_scan_response,
            scan_count_type="deployer_wallet_scan",
            processing_message_text="🔍 Analyzing token deployer wallet... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the deployer wallet. Please try again later.",
            no_data_message_text="❌ Could not find deployer wallet data for this token."
        )

    elif expecting == "top_holders_token_address":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="top_holders",
            get_data_func=get_token_top_holders,
            format_response_func=format_top_holders_response,
            scan_count_type="top_holders_scan",
            processing_message_text="🔍 Analyzing token's top holders... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the token's top holders. Please try again later.",
            no_data_message_text="❌ Could not find top holders data for this token."
        )
    
    elif expecting == "high_net_worth_holders_token_address":
        await handle_token_analysis_input(
            update=update,
            context=context,
            analysis_type="high_net_worth_holders",
            get_data_func=get_high_net_worth_holders,
            format_response_func=format_high_net_worth_holders_response,
            scan_count_type="high_net_worth_holders_scan",
            processing_message_text="🔍 Analyzing token's high net worth holders... This may take a moment.",
            error_message_text="❌ An error occurred while analyzing the token's high net worth holders. Please try again later.",
            no_data_message_text="❌ Could not find high net worth holders data for this token."
        )  

# help handlers
async def handle_general_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query

    general_help_text = (
        "<b>🆘 Welcome to DeFi-Scope Help Center</b>\n\n"
        "I’m your trusted assistant for navigating the world of DeFi. Use me to analyze tokens, uncover wallet activity, and monitor top-performing or suspicious wallets across the blockchain. 🔍📈\n\n"
        
        "<b>📊 Token Analysis:</b>\n"
        "🔹 View the <b>first buyers</b> of any token (1-50 wallets) with full trade stats and PNL.\n"
        "🔹 Track the <b>All-Time High (ATH)</b> market cap of any token, and its current standing.\n"
        "🔹 Discover <b>most profitable wallets</b> holding a specific token.\n"
        "🔹 (Premium) Reveal the <b>deployer wallet</b> behind a token and their past projects.\n"
        "🔹 (Premium) Check <b>top holders</b> and whales, and track their activity.\n"
        "🔹 (Premium) Identify <b>High Net Worth wallets</b> with $10,000+ in token holdings.\n\n"
        
        "<b>🕵️ Wallet Analysis:</b>\n"
        "🔹 Analyze <b>wallet holding duration</b> – how long they hold tokens before selling.\n"
        "🔹 Discover <b>most profitable wallets</b> over 1 to 30 days.\n"
        "🔹 Find <b>top token deployer wallets</b> and their earnings.\n"
        "🔹 (Premium) View <b>all tokens deployed</b> by any wallet and their performance.\n\n"
        
        "<b>🔔 Tracking & Monitoring:</b>\n"
        "🔹 (Premium) <b>Track wallet buy/sell</b> actions in real-time.\n"
        "🔹 (Premium) Get alerts when a <b>wallet deploys new tokens</b> or is linked to new ones.\n"
        "🔹 (Premium) Analyze <b>profitable wallets</b> in any token across full metrics (PNL, trades, volume).\n\n"
        
        "<b>📢 KOL & Whale Monitoring:</b>\n"
        "🔹 Monitor <b>KOL wallets</b> and their profit/loss over time.\n"
        "🔹 (Premium) Get alerts when <b>top 10 holders or whales</b> buy or dump a token.\n\n"
        
        "<b>💎 Premium Access:</b>\n"
        "Unlock all features, unlimited scans, and powerful tracking with a Premium plan.\n\n"
        "Tap a button from the menu to start using a feature, or hit ⬅️ Back to return.\n"
        "Happy hunting in the DeFi jungle! 🌐🚀"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Token Analysis", callback_data="token_analysis_help"),
            InlineKeyboardButton("🕵️ Wallet Analysis", callback_data="wallet_analysis_help")
         ],
        [
            InlineKeyboardButton("🔔 Tracking & Monitoring",  callback_data="tracking_and_monitoring_help"),
            InlineKeyboardButton("🐳 KOL & Whale Monitoring", callback_data="kol_wallet_help")
        ],
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
    """Handle token analysis button callback"""
    query = update.callback_query
    
    token_analysis_help_text = (
        "<b>📊 TOKEN ANALYSIS HELP</b>\n\n"
        "Use these features to deeply analyze any token across the blockchain. 🔎📈\n\n"

        "<b>🏁 First Buyers & Profits</b>\n"
        "🔹 See the first 1-50 wallets that bought a token with full stats:\n"
        "   - Buy & sell amount, total trades, PNL, and win rate.\n"
        "   - (Free: 3 token scans/day, Premium: Unlimited)\n\n"

        "<b>💰 Most Profitable Wallets</b>\n"
        "🔹 Discover the most profitable wallets holding a specific token.\n"
        "   - Includes buy & sell totals and net profit.\n"
        "   - (Free: 3 token scans/day, Premium: Unlimited)\n\n"

        "<b>📈 Market Cap & ATH</b>\n"
        "🔹 View the all-time high (ATH) market cap of any token.\n"
        "   - Includes ATH date and % from ATH.\n"
        "   - (Free: 3 token scans/day, Premium: Unlimited)\n\n"

        "<b>🧠 Deployer Wallet Scan</b> (Premium)\n"
        "🔹 Reveal the deployer wallet and all tokens deployed by it.\n"
        "   - Includes ATH market cap and x-multipliers.\n\n"

        "<b>🐋 Top Holders & Whale Watch</b> (Premium)\n"
        "🔹 See the top 10 holders and whale wallets of a token.\n"
        "🔹 Get notified when Dev, whales, or top 10 holders sell.\n\n"

        "<b>💎 High Net Worth Wallets</b> (Premium)\n"
        "🔹 Scan for wallets holding over $10,000 worth of a token.\n"
        "   - Includes total worth in USD, token amount, and average holding time.\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="token_analysis")]
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

async def handle_wallet_analysis_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    wallet_analysis_help_text = (
        "<b>🕵️ WALLET ANALYSIS HELP</b>\n\n"
        "Analyze individual wallets to uncover trading behavior and profitability. 🧠📊\n\n"

        "<b>💎 Most Profitable Wallets (1–30 days)</b>\n"
        "🔹 Track wallets with highest profits in short timeframes.\n"
        "   - Includes total buy amount and trade count.\n"
        "   - (Free: 2 wallets, Premium: Unlimited)\n\n"

        "<b>🕒 Wallet Holding Duration</b>\n"
        "🔹 Check how long a wallet holds tokens before selling.\n"
        "   - (Free: 3 wallet scans/day, Premium: Unlimited)\n\n"

        "<b>🧪 Most Profitable Token Deployer Wallets</b>\n"
        "🔹 Find top-earning deployers in the last 1–30 days.\n"
        "   - (Free: 2 wallets, Premium: Unlimited)\n\n"

        "<b>🧱 Tokens Deployed by Wallet</b> (Premium)\n"
        "🔹 Scan a wallet to view tokens it deployed.\n"
        "   - Includes name, ticker, price, deployment date, market cap, ATH.\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="wallet_analysis")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            wallet_analysis_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            wallet_analysis_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_tracking_and_monitoring_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    tracking_and_monitoring_help_text = (
    "<b>🔔 TRACKING & MONITORING HELP</b>\n\n"
    "Track wallets and token performance in real-time. Stay ahead of the game! ⚡👀\n\n"

    "<b>📈 Track Wallet Buy/Sell</b> (Premium)\n"
    "🔹 Get real-time alerts when a wallet buys or sells any token.\n\n"

    "<b>🧱 Track New Token Deployments</b> (Premium)\n"
    "🔹 Get notified when a wallet deploys a new token.\n"
    "🔹 Also alerts for new tokens linked to that wallet.\n\n"

    "<b>📊 Profitable Wallets of Any Token</b> (Premium)\n"
    "🔹 Track profitable wallets in any token.\n"
    "   - Full metrics: PNL, trades, volume, win rate (1–30 days).\n"
)

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="tracking_and_monitoring")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            tracking_and_monitoring_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            tracking_and_monitoring_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

async def handle_kol_wallets_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help button callback"""
    query = update.callback_query
    
    kol_wallets_help_text = (
        "<b>📢 KOL & WHALE MONITORING HELP</b>\n\n"
        "Track influencers, devs, and whales in the crypto market. 🐳🧠\n\n"

        "<b>📊 KOL Wallets Profitability</b>\n"
        "🔹 Track influencer wallets' PNL over 1–30 days.\n"
        "   - (Free: 3 scans/day, Premium: Unlimited)\n\n"

        "<b>🚨 Whale & Dev Sell Alerts</b> (Premium)\n"
        "🔹 Get alerts when:\n"
        "   - The developer sells\n"
        "   - Any top 10 holder sells\n"
        "   - Any whale wallet dumps the token\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="kol_wallets")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Try to edit the current message
        await query.edit_message_text(
            kol_wallets_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
    )
    except Exception as e:
        logging.error(f"Error in handle_back: {e}")
        # If editing fails, send a new message
        await query.message.reply_text(
            kol_wallets_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        # Delete the original message if possible
        try:
            await query.message.delete()
        except:
            pass

# main menu handlers
async def handle_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the main menu display"""

    if "default_network" not in context.user_data:
        context.user_data["default_network"] = "eth"  # Set Ethereum as default

    selected_network = context.user_data.get("default_network")
    network_display = {
        "eth": "🌐 Ethereum",
        "base": "🛡️ Base",
        "bsc": "🔶 BSC"
    }
    
    # If no network is selected, show network selection menu first
    if not selected_network:
        await handle_select_network(update, context)
        return
    
    welcome_message = (
        f"🆘 Welcome to <b>DeFi-Scope Bot, {update.effective_user.first_name}! 🎉</b>\n\n"
        f"🔎 <b>Your Ultimate DeFi Intelligence Bot!</b>\n"
        f"Stay ahead in the crypto game with powerful analytics, wallet tracking, and market insights. 📊💰\n\n"
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>📊 Token Analysis:</b>\n"
        f"🔹 <b>First Buyers & Profits of a token:</b> See the first 1-50 buy wallets of a token with buy & sell amount, buy & sell trades, total trades and PNL and win rate. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Most Profitable Wallets of a token:</b> See the most profitable wallets in any specific token with total buy & sell amount and profit. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Market Cap & ATH:</b>See all time high (ATH) market cap of any token with date and percentage of current market cap from ATH marketcap. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Deployer Wallet Scan:</b> (Premium) Scan a token contract to reveal the deployer wallet and show other tokens ever deployed by the deployer wallet and their all time high (ATH) marketcap and how many X's they did. \n"
        f"🔹 <b>Top Holders & Whale Watch:</b> (Premium) Scan a token contract to see top 10 holders, whale wallets holding the token.\n"
        f"🔹 <b>High Net Worth Wallet Holders:</b> (Premium) See the high net worth wallet holders of any token with total worth of at least $10,000 showing total worth in USD, coins/tokens held and amount and average holding time of the wallet.\n\n"
        f"<b>🕵️ Wallet Analysis:</b>\n"
        f"🔹 <b>Most profitable wallets in a specific period:</b>See the most profitable wallets in 1 to 30 days with total buy amount and number of trades. (Free users get only 2 most profitable wallets from this query. Premium users get unlimited)\n"
        f"🔹 <b>Wallet Holding Duration:</b> See how long a wallet holds a token before selling. (Maximum 3 wallet scans daily only for free users. Unlimited wallet scans daily for premium users)\n"
        f"🔹 <b>Most profitable token deployer wallets:</b> See the most profitable token deployer wallets in 1 to 30 days. (Free users only get 2 most profitable token deployer wallets from this query. Premium users get unlimited)\n"
        f"🔹 <b>Tokens Deployed by Wallet:</b> (Premium) See the tokens deployed by a particular wallet showing token name, ticker/symbol, current price, date of deployment, current market cap and All Time High (ATH) market cap.\n\n"
        f"<b>🔔 Tracking & Monitoring:</b>\n"
        f"🔹 <b>Track Buy/Sell Activity:</b> (Premium) Track a wallet to be notified when the wallet buys or sells any token.\n"
        f"🔹 <b>Track New Token Deployments:</b> (Premium) Track a wallet to be notified when that wallet deploys a new token or any of the wallet it's connected to deploys a new token.\n"
        f"🔹 <b>Profitable Wallets of any token:</b> (Premium) Track the profitable wallets in any token with total maximum number of trades, PNL, buy amount, sell amount, buy volume, sell volume, and win rate within 1 to 30 days.\n\n"
        f"<b>🐳 KOL wallets:</b>\n"
        f"🔹 <b>KOL Wallets Profitability:</b> Track KOL wallets profitability in 1-30 days with wallet name and PNL. (Maximum 3 scans daily only for free users. Unlimited scans daily for premium users)\n"
        f"🔹 <b>Track Whale Wallets:</b> (Premium) Track when the Dev sells, any of the top 10 holders sell or any of the whale wallets sell that token.\n\n"
        f"Happy Trading! 🚀💰"
    )
    
    keyboard_main = [
        [
            InlineKeyboardButton("📊 Token Analysis", callback_data="token_analysis"),
            InlineKeyboardButton("🕵️ Wallet Analysis", callback_data="wallet_analysis"),
        ],
        [
            InlineKeyboardButton("🔔 Tracking & Monitoring", callback_data="tracking_and_monitoring"),
            InlineKeyboardButton("🐳 KOL wallets", callback_data="kol_wallets")
        ],
        [
            InlineKeyboardButton(f"🔗 Network ({network_display.get(selected_network, selected_network.upper())})", callback_data="select_network"),
            InlineKeyboardButton("❓ Help", callback_data="general_help"),
        ],
        # [
        #     InlineKeyboardButton("🔙 Back", callback_data="back")
        # ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard_main)
    
    # Check if this is a callback query or a direct message
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Error editing message in handle_start_menu: {e}")
            await update.callback_query.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            try:
                await update.callback_query.message.delete()
            except:
                pass
    else:
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_select_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle network selection from main menu"""
    query = update.callback_query
    
    # Get currently selected network
    current_network = context.user_data.get("default_network", "eth")  # Default to Ethereum if none set
    
    # Create network button labels with current indicator
    eth_label = "🌐 Ethereum (Current)" if current_network == "eth" else "🌐 Ethereum" 
    base_label = "🛡️ Base (Current)" if current_network == "base" else "🛡️ Base" 
    bsc_label = "🔶 BSC (Current)" if current_network == "bsc" else "🔶 BSC"
    
    # Create keyboard with network options
    keyboard = [
        [
            InlineKeyboardButton(eth_label, callback_data="set_default_network_eth"),
            InlineKeyboardButton(base_label, callback_data="set_default_network_base"),
            InlineKeyboardButton(bsc_label, callback_data="set_default_network_bsc"),
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show network selection message
    await query.message.reply_text(
        "🔗 <b>Select Blockchain Network</b>\n\n"
        "Please choose the blockchain network you'd like to use for token and wallet analyses. Each chain has its own ecosystem, speed, and opportunities:\n\n"
        "• <b>🌐 Ethereum</b>: The original smart contract platform\n"
        "• <b>🛡️ Base</b>: Coinbase's Ethereum L2 solution\n"
        "• <b>🔶 BSC</b>: Binance Smart Chain (BNB Chain)\n\n"
        "This setting will be used for all token and wallet analyses.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_set_default_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle setting default network"""
    query = update.callback_query
    callback_data = query.data
    
    # Extract network from callback data
    # Format: "set_default_network_{network}"
    network = callback_data.replace("set_default_network_", "")
    
    # Map of network to display name
    network_display = {
        "eth": "🌐 Ethereum",
        "base": "🛡️ Base",
        "bsc": "🔶 BSC"
    }
    
    # Store the selected network in user_data
    context.user_data["default_network"] = network
    
    # Confirm selection
    await query.answer(f"Network set to {network_display.get(network, network.upper())}")
    
    # Return to main menu with the selected network
    await handle_start_menu(update, context)

async def handle_token_analysis(update:Update, context:ContextTypes.DEFAULT_TYPE)->None: 
    """Handle token analysis button"""

    if not context.user_data.get("default_network"):
        await handle_select_network(update, context)
        return

    welcome_message = (
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>📊 Token Analysis:</b>\n\n"
        f"🔹 <b>First Buyers & Profits of a token:</b> See the first 1-50 buy wallets of a token with buy & sell amount, buy & sell trades, total trades and PNL and win rate. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Most Profitable Wallets of a token:</b> Most profitable wallets in any specific token with total buy & sell amount and profit. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Market Cap & ATH:</b>All time high (ATH) market cap of any token with date and percentage of current market cap from ATH marketcap. (Maximum 3 token scans daily only for free users. Unlimited token scans daily for premium users)\n"
        f"🔹 <b>Deployer Wallet Scan:</b> (Premium) Scan a token contract to reveal the deployer wallet and show other tokens ever deployed by the deployer wallet and their all time high (ATH) marketcap and how many X's they did.\n"
        f"🔹 <b>Top Holders & Whale Watch:</b> (Premium) Scan a token contract to see top 10 holders, whale wallets holding the token.\n"
        f"🔹 <b>High Net Worth Wallet Holders:</b> (Premium) High net worth wallet holders of any token with total worth of at least $10,000 showing total worth in USD, coins/tokens held and amount and average holding time of the wallet.\n"
        f"🔹 <b>💎 Upgrade to Premium:</b> Unlock unlimited scans and premium features.\n"
        f"🔹 <b>Show Help:</b> Display this help menu anytime.\n\n"
        f"Happy Trading! 🚀💰"
    )

    token_analysis_keyboard = [
        [InlineKeyboardButton("🛒 First Buyers & Profits of a token", callback_data="token_first_buyers")],
        [InlineKeyboardButton("💰 Most Profitable Wallets of a token", callback_data="token_most_profitable_wallets")],
        [InlineKeyboardButton("📈 Market Cap & ATH of a token", callback_data="token_ath")],
        [InlineKeyboardButton("🧑‍💻 Deployer Wallet Scan (Premium)", callback_data="token_deployer_wallet_scan")],
        [InlineKeyboardButton("🐳 Top Holders & Whale Watch (Premium)", callback_data="token_top_holders")],
        [InlineKeyboardButton("💼 High Net Worth Holders (Premium)", callback_data="token_high_net_worth_holders")],
        [
            InlineKeyboardButton("❓ Help", callback_data="token_analysis_help"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(token_analysis_keyboard)
    
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

async def handle_wallet_analysis(update:Update, context:ContextTypes.DEFAULT_TYPE)->None: 
    """Handle wallet analysis button"""
    
    welcome_message = (
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>🕵️ Wallet Analysis:</b>\n\n"
        f"🔹 <b>Most profitable wallets in a specific period:</b>Most profitable wallets in 1 to 30 days with total buy amount and number of trades. (Free users get only 2 most profitable wallets from this query. Premium users get unlimited)\n"
        f"🔹 <b>Wallet Holding Duration:</b> See how long a wallet holds a token before selling. (Maximum 3 wallet scans daily only for free users. Unlimited wallet scans daily for premium users)\n"
        f"🔹 <b>Most profitable token deployer wallets:</b> See the most profitable token deployer wallets in 1 to 30 days. (Free users only get 2 most profitable token deployer wallets from this query. Premium users get unlimited)\n"
        f"🔹 <b>Tokens Deployed by Wallet:</b> (Premium) See the tokens deployed by a particular wallet showing token name, ticker/symbol, current price, date of deployment, current market cap and All Time High (ATH) market cap.\n\n"
        f"🔹 <b>Show Help:</b> Display this help menu anytime.\n\n"
        f"Happy Trading! 🚀💰"
    )
    wallet_tracking_keyboard = [
        [InlineKeyboardButton("💹 Most profitable wallets in specific period", callback_data="wallet_most_profitable_in_period")],
        [InlineKeyboardButton("💰 Most profitable token deployer wallets in period", callback_data="most_profitable_token_deployer_wallet")],
        [InlineKeyboardButton("⏳ Wallet Holding Duration", callback_data="wallet_holding_duration")],
        [InlineKeyboardButton("🚀 Tokens Deployed by Wallet (Premium)", callback_data="tokens_deployed_by_wallet")],
        [
            InlineKeyboardButton("❓ Help", callback_data="wallet_analysis_help"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(wallet_tracking_keyboard)
    
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

async def handle_tracking_and_monitoring(update:Update, context:ContextTypes.DEFAULT_TYPE)->None: 
    """Handle tracking and monitoring button"""
    welcome_message = (
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>🔔 Tracking & Monitoring:</b>\n\n"
        f"🔹 <b>Track Buy/Sell Activity:</b> (Premium) Track a wallet to be notified when the wallet buys or sells any token.\n"
        f"🔹 <b>Track New Token Deployments:</b> (Premium) Track a wallet to be notified when that wallet deploys a new token or any of the wallet it's connected to deploys a new token.\n"
        f"🔹 <b>Profitable Wallets of any token:</b> (Premium) Track the profitable wallets in any token with total maximum number of trades, PNL, buy amount, sell amount, buy volume, sell volume, and win rate within 1 to 30 days.\n"
        f"🔹 <b>Show Help:</b> Display this help menu anytime.\n\n"
        f"Happy Trading! 🚀💰"
    )

    tracking_and_monitoring_keyboard = [
        [InlineKeyboardButton("📥 Track Buy/Sell Activity (Premium)", callback_data="track_wallet_buy_sell")],
        [InlineKeyboardButton("🧬 Track Token Deployments (Premium)", callback_data="track_new_token_deploy")],
        [InlineKeyboardButton("📊 Profitable Wallets of a token(Premium)", callback_data="track_profitable_wallets")],
        [
            InlineKeyboardButton("❓ Help", callback_data="tracking_and_monitoring_help"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(tracking_and_monitoring_keyboard)
    
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

async def handle_kol_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle kol wallets button"""
    welcome_message = (
        f"✨ <b>What can I do for you?</b>\n\n"
        f"<b>🐳 KOL wallets:</b>\n\n"
        f"🔹 <b>KOL Wallets Profitability:</b> Track KOL wallets profitability in 1-30 days with wallet name and PNL. (Maximum 3 scans daily only for free users. Unlimited scans daily for premium users)\n"
        f"🔹 <b>Track Whale Wallets:</b> (Premium) Track when the Dev sells, any of the top 10 holders sell or any of the whale wallets sell that token\n"
        f"🔹 <b>Show Help:</b> Display this help menu anytime.\n\n"
        f"Happy Trading! 🚀💰"
    )
    token_analysis_keyboard = [
        [InlineKeyboardButton("📢 KOL Wallets Profitability", callback_data="kol_wallet_profitability")],
        [InlineKeyboardButton("🐳 Track Whalet Wallets(Premium)", callback_data="track_whale_wallets")],
        [
            InlineKeyboardButton("❓ Help", callback_data="kol_wallets_help"),
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(token_analysis_keyboard)
    
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

# token analysis handlers
async def handle_first_buyers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle first buyers button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user has reached daily limit
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "first_buy_wallet_scan", FREE_TOKEN_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"🧾 You've used <b>{current_count}</b> out of <b>{FREE_TOKEN_SCANS_DAILY}</b> free daily scans for <b>First Buyers Analysis</b>.\n"
            f"This tool lets you discover who bought early, how much they earned, and their trading behavior. Great for identifying smart money moves! 💸\n\n"
            f"💎 <b>Upgrade to Premium</b> for unlimited scans and deeper DeFi intelligence:\n"
            f"• Analyze unlimited tokens 🔄\n"
            f"• Track early buyers & their profit trends 📈\n"
            f"• Get wallet insights, market cap data, and more! 🚀\n\n"
            f"🔓 Unlock the full potential of DeFi-Scope with Premium access!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    await handle_token_analysis_token_input(update, context, "first_buyers")

async def handle_token_most_profitable_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle most profitable wallets button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user has reached daily limit
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "token_most_profitable_wallet_scan", FREE_TOKEN_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"📊 You've used <b>{current_count}</b> out of <b>{FREE_TOKEN_SCANS_DAILY}</b> daily scans for <b>Most Profitable Wallets</b>.\n"
            f"This feature helps you uncover top-performing wallets in any token — who's buying, who's profiting, and how much! 🧠💰\n\n"
            f"💎 <b>Premium users enjoy unlimited scans</b> and access to full profitability metrics:\n"
            f"• Unlimited wallet analysis 🔍\n"
            f"• Identify winning traders and copy their strategy 📥\n"
            f"• Gain edge over the market with real wallet data 🧩\n\n"
            f"🚀 Ready to level up? <b>Unlock Premium now!</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to select a chain
    await handle_token_analysis_token_input(update, context, "token_most_profitable_wallets")

async def handle_ath(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ATH button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user has reached daily limit
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "ath_scan", FREE_TOKEN_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"🚫 You've used <b>{current_count}</b> out of <b>{FREE_TOKEN_SCANS_DAILY}</b> free daily token scans.\n"
            f"Free users can analyze up to {FREE_TOKEN_SCANS_DAILY} tokens each day to explore market caps, trends, and ATH insights.\n\n"
            f"💎 <b>Premium users get unlimited scans</b> — no restrictions, no waiting!\n"
            f"Unlock powerful features like:\n"
            f"• Unlimited token & wallet scans 🔍\n"
            f"• Full deployer history & token performance 🧠\n"
            f"• Real-time tracking alerts 📡\n"
            f"• Whale & KOL wallet monitoring 🐋\n\n"
            f"🚀 <b>Upgrade now and dive deeper into DeFi intelligence!</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to select a chain
    await handle_token_analysis_token_input(update, context, "ath")

async def handle_deployer_wallet_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deployer wallet scan button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "🔐 <b>Deployer Wallet Scanning</b> is an advanced feature available only to <b>Premium</b> users.\n"
            "This feature reveals the original wallet that launched the token and provides:\n"
            "• A full list of other tokens they’ve deployed 🪙\n"
            "• Performance stats including ATH market caps 📊\n"
            "• Insight into how many X’s they did 📈\n\n"
            "💡 Perfect for spotting patterns and identifying smart (or shady) deployers early!\n\n"
            "💎 <b>Upgrade to Premium</b> now to unlock this and many more pro features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
        
    # Prompt user to select a chain
    await handle_token_analysis_token_input(update, context, "deployer_wallet_scan")

async def handle_top_holders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle top holders button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "🔍 <b>Top Holders & Whale Analysis</b> is an advanced feature available only to <b>Premium</b> users. It gives you the insight:\n"
            "• The top 10 wallets holding a token 👑\n"
            "• Dev and whale activity (when they buy/sell) 📉📈\n"
            "• Early warnings of dumps or big moves 📡\n\n"
            "This powerful tool is only available for <b>Premium users</b>.\n\n"
            "💎 <b>Upgrade to Premium</b> and gain full access to:\n"
            "• Real-time tracking of whales & top holders\n"
            "• Token movement alerts\n"
            "• Unlimited scans and insights\n\n"
            "🚀 Stay one step ahead with DeFi intelligence!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to select a chain
    await handle_token_analysis_token_input(update, context, "top_holders")

async def handle_high_net_worth_holders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle high net worth token holders button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "💰 <b>High Net Worth Holders</b> analysis shows you:\n"
            "• Wallets holding over $10,000+ in value 💸\n"
            "• Total token worth, quantity held, and average hold time ⏳\n"
            "• Wallets that move markets – instantly spot smart money moves 🧠\n\n"
            "This elite-level insight is exclusive to <b>Premium users</b>.\n\n"
            "💎 <b>Upgrade to Premium</b> to unlock:\n"
            "• Full visibility into major token holders\n"
            "• Premium-level scan tools and unlimited access\n"
            "• Strategy-altering on-chain data\n\n"
            "🔓 Get access to what whales are doing behind the scenes!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to select a chain
    await handle_token_analysis_token_input(update, context, "high_net_worth_holders")


# wallet analysis handlers
async def handle_wallet_most_profitable_in_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle most profitable wallets in period button callback"""
    
    await handle_period_selection(
        update=update,
        context=context,
        feature_info="Most Profitable Wallets Analysis",
        scan_type="wallet_most_profitable_in_period_scan",
        callback_prefix="profitable_period"
    )

async def handle_wallet_holding_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle wallet holding duration button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user has reached daily limit
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "wallet_scan", FREE_WALLET_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {FREE_WALLET_SCANS_DAILY} daily wallet scans.\n\n"
            f"Premium users enjoy unlimited scans! 💎<b>Upgrade to Premium</b> for more features.\n\n",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address to analyze its token holding duration.\n\n"
        "Example: `0x1234...abcd`\n\n"
        "I'll analyze how long this wallet typically holds tokens before selling.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for holding duration analysis
    context.user_data["expecting"] = "wallet_holding_duration_address"
    
    # Increment the scan count for this user
    await increment_scan_count(user.user_id, "wallet_scan")

async def handle_most_profitable_token_deployer_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await handle_period_selection(
        update=update,
        context=context,
        feature_info="Most Profitable Token Deployer Wallets Analysis",
        scan_type="most_profitable_token_depolyer_wallet_in_period_scan",
        callback_prefix="deployer_period"
    )
    
async def handle_tokens_deployed_by_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tokens deployed by wallet button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tokens Deployed by Wallet analysis is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address to find all tokens deployed by this wallet.\n\n"
        "Example: `0x1234...abcd`\n\n"
        "I'll analyze and show you all tokens this wallet has deployed.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for tokens deployed analysis
    context.user_data["expecting"] = "tokens_deployed_wallet_address"


async def handle_period_selection_callback(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    get_data_func,
    format_response_func,
    scan_count_type: str,
    processing_message_text: str,
    error_message_text: str,
    no_data_message_text: str,
    free_limit: int = FREE_RESPONSE_DAILY,
    premium_limit: int = 10
) -> None:
    """
    Generic handler for period selection callbacks
    
    Args:
        update: The update object
        context: The context object
        get_data_func: Function to get the data
        format_response_func: Function to format the response
        scan_count_type: Type of scan to increment count for
        processing_message_text: Text to show while processing
        error_message_text: Text to show on error
        no_data_message_text: Text to show when no data is found
        free_limit: Limit for free users
        premium_limit: Limit for premium users
    """
    query = update.callback_query
    user = await check_callback_user(update)
    
    selected_period = int(query.data.split("_")[-1])
    logging.info(f"Selected period: {selected_period} days")
    
    # Store the selected period in context
    context.user_data["selected_period"] = selected_period
    
    # Get the selected chain
    selected_chain = context.user_data.get("selected_chain", "eth")
    logging.info(f"Selected chain: {selected_chain}")    
    # Process the request
    processing_message = await query.edit_message_text(
        processing_message_text.format(days=selected_period)
    )
    
    try:
        # For free users, limit the number of results
        limit = premium_limit if user.is_premium else free_limit
        logging.info(f"User is premium: {user.is_premium}, using limit: {limit}")
        logging.info(f"Calling get_data_func with days={selected_period}, limit={limit}, chain={selected_chain}")

        data = await get_data_func(
            days=selected_period,
            limit=limit,
            chain=selected_chain
        )
        
        if not data:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                no_data_message_text,
                reply_markup=reply_markup
            )
            return
        
        # Format the response
        response, keyboard = format_response_func(data)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Increment scan count
        await increment_scan_count(user.user_id, scan_count_type)
        
    except Exception as e:
        logging.error(f"Error in handle_period_selection_callback: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            error_message_text,
            reply_markup=reply_markup
        )

async def handle_profitable_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle selection of time period for profitable wallets analysis"""
    logging.info("Welcome to handle_profitable_period_selection_callback")
    
    await handle_period_selection_callback(
        update=update,
        context=context,
        scan_count_type="wallet_most_profitable_in_period_scan",
        get_data_func=get_wallet_most_profitable_in_period,
        format_response_func=format_wallet_most_profitable_response,
        processing_message_text="🔍 Finding most profitable wallets in the last {days} days... This may take a moment.",
        error_message_text="❌ An error occurred while analyzing profitable wallets. Please try again later.",
        no_data_message_text="❌ Could not find profitable wallets for this period.",
        free_limit=FREE_RESPONSE_DAILY,
        premium_limit=PREMIUM_RESPONSE_DAILY
    )

async def handle_deployer_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle selection of time period for profitable token deployer wallets analysis"""
    
    await handle_period_selection_callback(
        update=update,
        context=context,
        get_data_func=get_most_profitable_token_deployer_wallets,
        format_response_func=format_deployer_wallets_response,
        scan_count_type="most_profitable_token_deployer_scan",
        processing_message_text="🔍 Finding most profitable token deployers in the last {days} days... This may take a moment.",
        error_message_text="❌ An error occurred while analyzing profitable token deployers. Please try again later.",
        no_data_message_text="❌ Could not find profitable token deployers for this period.",
        free_limit=FREE_RESPONSE_DAILY,
        premium_limit=PREMIUM_RESPONSE_DAILY
    )

# track and monitoring handlers
async def handle_track_wallet_buy_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track wallet buy/sell button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking wallet buy/sell activity is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address you want to track for buy/sell activities.\n\n"
        "Example: `0x1234...abcd`\n\n"
        "You'll receive notifications when this wallet makes significant trades.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for tracking
    context.user_data["expecting"] = "track_wallet_buy_sell_address"

async def handle_track_new_token_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track new token deployments button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking new token deployments is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter wallet address
    await query.edit_message_text(
        "Please send me the wallet address you want to track for new token deployments.\n\n"
        "Example: `0x1234...abcd`\n\n"
        "You'll receive notifications when this wallet deploys new tokens.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect wallet address for tracking
    context.user_data["expecting"] = "track_new_token_deploy_address"

async def handle_track_profitable_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track profitable wallets button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking profitable wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send processing message
    processing_message = await query.edit_message_text(
        "🔍 Finding most profitable wallets to track... This may take a moment."
    )
    
    try:
        # Get profitable wallets (last 30 days, top 5)
        profitable_wallets = await get_profitable_wallets(30, 5)
        
        if not profitable_wallets:
            await processing_message.edit_text(
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
        
        # Format the response
        response = f"✅ <b>Now tracking top 5 profitable wallets:</b>\n\n"
        
        for i, wallet in enumerate(profitable_wallets[:5], 1):
            response += (
                f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
                f"   Profit: ${wallet.get('total_profit', 'N/A')}\n\n"
            )
        
        response += "You will receive notifications when these wallets make significant trades."
        
        # Add button to go back
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_track_profitable_wallets: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while setting up tracking. Please try again later."
        )

# KOL wallets handlers
async def handle_kol_wallet_profitability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle KOL wallet profitability button callback"""
    query = update.callback_query
    
    # Send processing message
    processing_message = await query.edit_message_text(
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
        
        for i, wallet in enumerate(kol_wallets[:5], 1):  # Show top 5 KOLs
            response += (
                f"{i}. {wallet.get('name', 'Unknown KOL')}\n"
                f"   Wallet: `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
                f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
                f"   Profit: ${wallet.get('total_profit', 'N/A')}\n\n"
            )
        
        # Add button to see more KOLs
        keyboard = [
            [InlineKeyboardButton("See More KOLs", callback_data="more_kols")],
            [InlineKeyboardButton("Track KOL Wallets", callback_data="track_kol_wallets")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_kol_wallet_profitability: {e}")
        await processing_message.edit_text(
            "❌ An error occurred while analyzing KOL wallets. Please try again later."
        )

async def handle_track_whale_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track whale wallets button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking whale wallets is only available to premium users.\n\n"
            "Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Prompt user to enter token address
    await query.edit_message_text(
        "Please send me the token contract address to track its whale wallets.\n\n"
        "Example: `0x1234...abcd`\n\n"
        "I'll set up tracking for the top holders of this token.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Set conversation state to expect token address for whale tracking
    context.user_data["expecting"] = "track_whale_wallets_token"


async def handle_token_analysis_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str) -> None:
    """
    Generic function to prompt user to select a blockchain network
    
    Args:
        update: The update object
        context: The context object
        feature: The feature identifier (e.g., 'first_buyers', 'ath', etc.)
    """
    query = update.callback_query
    
    # Use the default network directly
    chain = context.user_data.get("default_network")
    print(f"Selected chain for first buyers: {chain}")
    
    # Store the selected chain in user_data
    # context.user_data["selected_chain"] = chain
    
    # Map of feature to expecting state and display name
    feature_map = {
        "first_buyers": {
            "expecting": "first_buyers_token_address",
            "display": "first buyers"
        },
        "token_most_profitable_wallets": {
            "expecting": "token_most_profitable_wallets_token_address",
            "display": "most profitable wallets"
        },
        "ath": {
            "expecting": "ath_token_address",
            "display": "ATH data"
        },
        "deployer_wallet_scan": {
            "expecting": "deployer_wallet_scan_token",
            "display": "deployer wallet"
        },
        "top_holders": {
            "expecting": "top_holders_token_address",
            "display": "top holders"
        },
        "high_net_worth_holders": {
            "expecting": "high_net_worth_holders_token_address",
            "display": "high net worth holders"
        }
    }

    # Map of chain to display name
    chain_display = {
        "eth": "🌐 Ethereum",
        "base": "🛡️ Base",
        "bsc": "🔶 BSC"
    }
    
    # Get feature info
    feature_info = feature_map.get(feature, {"expecting": "unknown", "display": feature})
    print(f"feature_info for first_buyers: {feature_info}")
    
    # Prompt user to enter token address with back button
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"🔍 <b>Token Analysis on {chain_display.get(chain, chain.upper())}</b>\n\n"
        f"Please send me the token contract address to analyze its {feature_info['display']}.\n\n"
        f"Example: `0x1234...abcd`",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Set conversation state to expect token address for the specific feature
    context.user_data["expecting"] = feature_info["expecting"]

async def handle_chain_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chain selection callbacks"""
    query = update.callback_query
    callback_data = query.data
    
    # Extract feature and chain from callback data
    # Format: "{feature}_chain_{chain}"
    parts = callback_data.split("_chain_")
    if len(parts) != 2:
        await query.answer("Invalid selection", show_alert=True)
        return
    
    feature = parts[0]
    chain = parts[1]
    
    # Store the selected chain in user_data
    context.user_data["selected_chain"] = chain
    
    # Map of feature to expecting state and display name
    feature_map = {
        "first_buyers": {
            "expecting": "first_buyers_token_address",
            "display": "first buyers"
        },
        "token_most_profitable_wallets": {
            "expecting": "token_most_profitable_wallets_token_address",
            "display": "most profitable wallets"
        },
        "ath": {
            "expecting": "ath_token_address",
            "display": "ATH data"
        },
        "deployer_wallet_scan": {
            "expecting": "deployer_wallet_scan_token",
            "display": "deployer wallet"
        },
        "top_holders": {
            "expecting": "top_holders_token_address",
            "display": "top holders"
        },
        "high_net_worth_holders": {
            "expecting": "high_net_worth_holders_token_address",
            "display": "high net worth holders"
        }
    }
    
    # Map of chain to display name
    chain_display = {
        "eth": "🌐 Ethereum",
        "base": "🛡️ Base",
        "bsc": "🔶 BSC"
    }
    
    # Get feature info
    feature_info = feature_map.get(feature, {"expecting": "unknown", "display": feature})
    
    # Prompt user to enter token address with back button
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🔍 <b>Token Analysis on {chain_display.get(chain, chain.upper())}</b>\n\n"
        f"Please send me the token contract address to analyze its {feature_info['display']}.\n\n"
        f"Example: `0x1234...abcd`",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Set conversation state to expect token address for the specific feature
    context.user_data["expecting"] = feature_info["expecting"]






async def handle_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium info callback"""
    query = update.callback_query
    
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
    
    premium_text = (
        "⭐ <b>Upgrade to DeFi-Scope Premium</b>\n\n"

        "<b>🚀 Why Go Premium?</b>\n"
        "Gain unlimited access to powerful tools that help you track tokens, analyze wallets, "
        "and monitor whales like a pro. With DeFi-Scope Premium, you'll stay ahead of the market and "
        "make smarter investment decisions.\n\n"

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
        "✅ <b>High Net Worth Wallet Monitoring:</b> Find wallets with high-value holdings and see how they invest.\n"
        "✅ <b>Priority Support:</b> Get faster responses and priority assistance from our support team.\n\n"

        "<b>💰 Premium Pricing Plans:</b>\n"
        "📅 <b>Weekly Plan:</b>\n"
        "• 0.1 ETH per week\n"
        "• 0.35 BNB per week\n\n"
        "📅 <b>Monthly Plan:</b>\n"
        "• 0.25 ETH per month\n"
        "• 1.0 BNB per month\n\n"

        "🔹 <b>Upgrade now</b> to unlock the full power of DeFi-Scope and take control of your investments!\n"
        "Select a plan below to get started:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🟢 Weekly - 🦄 0.1 ETH", callback_data="premium_plan_weekly_eth"),
            InlineKeyboardButton("🟢 Weekly - 🟡 0.35 BNB", callback_data="premium_plan_weekly_bnb")
        ],
        [
            InlineKeyboardButton("📅 Monthly - 🦄 0.25 ETH", callback_data="premium_plan_monthly_eth"),
            InlineKeyboardButton("📅 Monthly - 🟡 1.0 BNB", callback_data="premium_plan_monthly_bnb")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Error in handle_premium_info: {e}")
        await query.message.reply_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        try:
            await query.message.delete()
        except:
            pass

async def handle_premium_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, currency: str) -> None:
    """Handle premium purchase callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Get all payment details from a single function call
    payment_details = get_plan_payment_details(plan, currency)
    
    # Extract needed values from payment details
    wallet_address = payment_details["wallet_address"]
    crypto_amount = payment_details["amount"]
    duration_days = payment_details["duration_days"]
    display_name = payment_details["display_name"]
    display_price = payment_details["display_price"]
    network = payment_details["network"]
    currency_code = payment_details["currency"]
    
    # Determine network name for display
    network_name = "Ethereum" if network.lower() == "eth" else "Binance Smart Chain"
    
    # Show payment instructions with QR code
    payment_text = (
        f"🛒 <b>{display_name} Premium Plan</b>\n\n"
        f"Price: {display_price}\n"
        f"Duration: {duration_days} days\n\n"
        f"<b>Payment Instructions:</b>\n\n"
        f"1. Send <b>exactly {crypto_amount} {currency_code}</b> to our wallet address:\n"
        f"`{wallet_address}`\n\n"
        f"2. After sending, click 'I've Made Payment' and provide your transaction ID/hash.\n\n"
        f"<b>Important:</b>\n"
        f"• Send only {currency_code} on the {network_name} network\n"
        f"• Other tokens or networks will not be detected\n"
        f"• Transaction must be confirmed on the blockchain to activate premium"
    )
    
    # Store plan information in user_data for later use
    context.user_data["premium_plan"] = plan
    context.user_data["payment_currency"] = currency
    context.user_data["crypto_amount"] = crypto_amount
    
    keyboard = [
        [InlineKeyboardButton("I've Made Payment", callback_data=f"payment_made_{plan}_{currency}")],
        [InlineKeyboardButton("🔙 Back", callback_data="premium_info")]
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
        try:
            import qrcode
            from io import BytesIO
            
            # Create QR code with the wallet address and amount
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Format QR data based on currency
            if network.lower() == "eth":
                qr_data = f"ethereum:{wallet_address}?value={crypto_amount}"
            else:
                qr_data = f"binance:{wallet_address}?value={crypto_amount}"
                
            qr.add_data(qr_data)
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
                caption=f"Scan this QR code to pay {crypto_amount} {currency_code} to our wallet"
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

async def handle_payment_made(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, currency: str) -> None:
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
            context.user_data["payment_currency"] = currency
            
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="premium_info")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 <b>Transaction ID Required</b>\n\n"
                f"Please send the transaction hash/ID of your {currency.upper()} payment.\n\n"
                "You can find this in your wallet's transaction history after sending the payment.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        
        # 2. Get payment details based on the plan and currency
        payment_details = get_plan_payment_details(plan, currency)
        
        expected_amount = payment_details["amount"]
        wallet_address = payment_details["wallet_address"]
        duration_days = payment_details["duration_days"]
        network = payment_details["network"]
        
        # 3. Verify the payment on the blockchain
        from services.payment import verify_crypto_payment
        
        verification_result = await verify_crypto_payment(
            transaction_id=transaction_id,
            expected_amount=expected_amount,
            wallet_address=wallet_address,
            network=network
        )
        
        # 4. Process verification result
        if verification_result["verified"]:
            # Calculate premium expiration date
            from datetime import datetime, timedelta
            now = datetime.now()
            premium_until = now + timedelta(days=duration_days)
            
            # Update user's premium status in the database
            from data.database import update_user_premium_status
            
            # Update user status
            update_user_premium_status(
                user_id=user.user_id,
                is_premium=True,
                premium_until=premium_until,
                plan=plan,
                payment_currency=currency,
                transaction_id=transaction_id
            )
            
            # Clear transaction data from user_data
            if "transaction_id" in context.user_data:
                del context.user_data["transaction_id"]
            
            # Log successful premium activation
            logging.info(f"Premium activated for user {user.user_id}, plan: {plan}, currency: {currency}, until: {premium_until}")
            
            # Create confirmation message with back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send confirmation to user
            await query.edit_message_text(
                f"✅ <b>Payment Verified - Premium Activated!</b>\n\n"
                f"Thank you for upgrading to DeFi-Scope Premium.\n\n"
                f"<b>Transaction Details:</b>\n"
                f"• Plan: {plan.capitalize()}\n"
                f"• Amount: {expected_amount} {currency.upper()}\n"
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
                    f"• Expected payment: {expected_amount} {currency.upper()}\n"
                    f"• Received payment: {received} {currency.upper()}\n"
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
                [InlineKeyboardButton("Try Again", callback_data=f"payment_retry_{plan}_{currency}")],
                [InlineKeyboardButton("Contact Support", url="https://t.me/SeniorCrypto01")],
                [InlineKeyboardButton("🔙 Back", callback_data="premium_info")]
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
            [InlineKeyboardButton("Try Again", callback_data=f"premium_plan_{plan}_{currency}")],
            [InlineKeyboardButton("Contact Support", url="https://t.me/SeniorCrypto01")],
            [InlineKeyboardButton("🔙 Back", callback_data="premium_info")]
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

async def handle_payment_retry(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, currency: str) -> None:
    """Handle payment retry callback"""
    query = update.callback_query
    
    # Clear the stored transaction ID
    if "transaction_id" in context.user_data:
        del context.user_data["transaction_id"]
    
    # Set up to collect a new transaction ID
    context.user_data["awaiting_transaction_id"] = True
    context.user_data["premium_plan"] = plan
    context.user_data["payment_currency"] = currency
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="premium_info")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 <b>New Transaction ID Required</b>\n\n"
        f"Please send the new transaction hash/ID of your {currency.upper()} payment.\n\n"
        "You can find this in your wallet's transaction history after sending the payment.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_transaction_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle transaction ID input from user"""
    # Check if we're awaiting a transaction ID
    if not context.user_data.get("awaiting_transaction_id"):
        return
    
    # Get the transaction ID from the message
    transaction_id = update.message.text.strip()
    
    # Basic validation - transaction IDs are typically hex strings starting with 0x
    if not (transaction_id.startswith("0x") and len(transaction_id) >= 66):
        await update.message.reply_text(
            "⚠️ <b>Invalid Transaction ID</b>\n\n"
            "The transaction ID should start with '0x' and be at least 66 characters long.\n"
            "Please check your wallet and send the correct transaction hash.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Store the transaction ID
    context.user_data["transaction_id"] = transaction_id
    
    # Get the plan and currency from user_data
    plan = context.user_data.get("premium_plan")
    currency = context.user_data.get("payment_currency")
    
    if not plan or not currency:
        await update.message.reply_text(
            "❌ <b>Error</b>\n\n"
            "Could not find your subscription plan details. Please start over.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Clear the awaiting flag
    context.user_data["awaiting_transaction_id"] = False
    
    # Send confirmation and start verification
    confirmation_message = await update.message.reply_text(
        f"✅ Transaction ID received: `{transaction_id[:8]}...{transaction_id[-6:]}`\n\n"
        f"Now verifying your payment on the {currency.upper()} blockchain...",
        parse_mode=ParseMode.HTML
    )
    
    # Create verification button
    keyboard = [
        [InlineKeyboardButton("Verify Payment", callback_data=f"payment_made_{plan}_{currency}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the message with a button to start verification
    await confirmation_message.edit_text(
        f"✅ Transaction ID received: `{transaction_id[:8]}...{transaction_id[-6:]}`\n\n"
        f"Click the button below to verify your payment on the {currency.upper()} blockchain.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )





# async def handle_th(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
#     """Handle top holders callback"""
#     query = update.callback_query
#     user = await check_callback_user(update)
    
#     # Check if user is premium
#     if not user.is_premium:
#         keyboard = [
#             [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
#             [InlineKeyboardButton("🔙 Back", callback_data="back")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             "⭐ <b>Premium Feature</b>\n\n"
#             "Top Holders Analysis is only available to premium users.\n\n"
#             "💎 Upgrade to premium to unlock all features!",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#         return
    
#     # Send processing message
#     await query.edit_message_text(
#         "🔍 Analyzing token top holders... This may take a moment."
#     )
    
#     try:
#         # Get token holders (placeholder - implement actual blockchain query)
#         holders = await get_token_holders(token_address)
#         token_data = await get_token_data(token_address)
        
#         if not holders or not token_data:
#             await query.edit_message_text(
#                 "❌ Could not find holder data for this token."
#             )
#             return
        
#         # Format the response
#         response = (
#             f"👥 <b>Top Holders for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
#         )
        
#         for i, holder in enumerate(holders[:10], 1):
#             percentage = holder.get('percentage', 'N/A')
#             response += (
#                 f"{i}. `{holder['address'][:6]}...{holder['address'][-4:]}`\n"
#                 f"   Holdings: {holder.get('amount', 'N/A')} tokens ({percentage}%)\n"
#                 f"   Value: ${holder.get('value', 'N/A')}\n\n"
#             )
        
#         # Add button to export data
#         keyboard = [
#             [InlineKeyboardButton("Export Full Data", callback_data=f"export_th_{token_address}")],
#             [InlineKeyboardButton("🔙 Back", callback_data="back")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             response,
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
    
#     except Exception as e:
#         logging.error(f"Error in handle_th: {e}")
#         await query.edit_message_text(
#             "❌ An error occurred while analyzing top holders. Please try again later."
#         )

# async def handle_dw(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
#     """Handle deployer wallet analysis callback"""
#     query = update.callback_query
#     user = await check_callback_user(update)
    
#     # Check if user is premium
#     if not user.is_premium:
#         keyboard = [
#             [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
#             [InlineKeyboardButton("🔙 Back", callback_data="back")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             "⭐ <b>Premium Feature</b>\n\n"
#             "Deployer Wallet Analysis is only available to premium users.\n\n"
#             "💎 Upgrade to premium to unlock all features!",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#         return
    
#     # Send processing message
#     await query.edit_message_text(
#         "🔍 Analyzing token deployer wallet... This may take a moment."
#     )
    
#     try:
#         # Get token info (placeholder - implement actual blockchain query)
#         token_data = await get_token_data(token_address)
        
#         if not token_data or not token_data.get('deployer_wallet'):
#             await query.edit_message_text(
#                 "❌ Could not find deployer wallet data for this token."
#             )
#             return
        
#         # Format the response
#         deployer = token_data.get('deployer_wallet', {})
#         response = (
#             f"🔎 <b>Deployer Wallet Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
#             f"Deployer Wallet: `{deployer.get('address', 'Unknown')}`\n\n"
#             f"Tokens Deployed: {deployer.get('tokens_deployed', 'N/A')}\n"
#             f"Success Rate: {deployer.get('success_rate', 'N/A')}%\n"
#             f"Avg. ROI: {deployer.get('avg_roi', 'N/A')}%\n"
#             f"Rugpull History: {deployer.get('rugpull_count', 'N/A')} tokens\n\n"
#             f"Risk Assessment: {deployer.get('risk_level', 'Unknown')}"
#         )
        
#         # Add button to track this deployer
#         keyboard = [
#             [InlineKeyboardButton("Track This Deployer", callback_data=f"track_deployer_{deployer.get('address', '')}")],
#             [InlineKeyboardButton("🔙 Back", callback_data="back")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             response,
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
    
#     except Exception as e:
#         logging.error(f"Error in handle_dw: {e}")
#         await query.edit_message_text(
#             "❌ An error occurred while analyzing deployer wallet. Please try again later."
#         )

# async def handle_track_token(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str) -> None:
#     """Handle track token callback"""
#     query = update.callback_query
#     user = await check_callback_user(update)
    
#     # Check if user is premium
#     if not user.is_premium:
#         keyboard = [
#             [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
#             [InlineKeyboardButton("🔙 Back", callback_data="back")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
        
#         await query.edit_message_text(
#             "⭐ <b>Premium Feature</b>\n\n"
#             "Token tracking is only available to premium users.\n\n"
#             "💎 Upgrade to premium to unlock all features!",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#         return
    
#     # Create tracking subscription
#     from data.models import TrackingSubscription
#     from datetime import datetime
    
#     subscription = TrackingSubscription(
#         user_id=user.user_id,
#         tracking_type="token",
#         target_address=token_address,
#         is_active=True,
#         created_at=datetime.now()
#     )
    
#     # Save subscription
#     from data.database import save_tracking_subscription
#     save_tracking_subscription(subscription)
    
#     # Get token data for name
#     token_data = await get_token_data(token_address)
#     token_name = token_data.get('name', 'Unknown Token') if token_data else 'this token'
    
#     # Confirm to user
#     await query.edit_message_text(
#         f"✅ Now tracking token: {token_name}\n\n"
#         f"Contract: `{token_address[:6]}...{token_address[-4:]}`\n\n"
#         f"You will receive notifications for significant price movements, "
#         f"whale transactions, and other important events.",
#         parse_mode=ParseMode.MARKDOWN
#     )

async def handle_track_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str) -> None:
    """Handle track wallet callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Wallet tracking is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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

async def handle_track_wallet_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track wallet trades button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking wallet trades is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking wallet deployments is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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

async def handle_track_whale_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle track whale sales button callback"""
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking whale and dev sales is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
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

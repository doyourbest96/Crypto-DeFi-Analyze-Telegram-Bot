import logging
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import FREE_TOKEN_SCANS_DAILY, FREE_WALLET_SCANS_DAILY
from data.database import get_token_data, get_wallet_data
from services.blockchain import is_valid_address, get_first_buyers, get_token_holders
from services.user_management import get_or_create_user, check_rate_limit_service
from handlers.callback_handlers import handle_start_menu, handle_payment_made, handle_expected_input

async def handle_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle transaction ID submission
    
    Returns:
        bool: True if this was a transaction ID message, False otherwise
    """
    # Check if we're waiting for a transaction ID
    if context.user_data.get("awaiting_transaction_id"):
        # Get the transaction ID from the message
        transaction_id = update.message.text.strip()
        
        # Validate transaction ID format (basic check for Ethereum transaction hash)
        if transaction_id.startswith("0x") and len(transaction_id) == 66:
            # Store the transaction ID
            context.user_data["transaction_id"] = transaction_id
            del context.user_data["awaiting_transaction_id"]
            
            # Get the plan from user data
            plan = context.user_data.get("premium_plan", "monthly")
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "🔄 Verifying your payment on the blockchain... This may take a moment."
            )
            
            # Create a dummy callback query for the payment handler
            class DummyCallback:
                def __init__(self, message, from_user):
                    self.message = message
                    self.from_user = from_user
                
                async def answer(self):
                    pass
                
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    return await self.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            
            dummy_callback = DummyCallback(processing_msg, update.effective_user)
            
            class DummyUpdate:
                def __init__(self, callback_query, effective_user, effective_chat):
                    self.callback_query = callback_query
                    self.effective_user = effective_user
                    self.effective_chat = effective_chat
            
            dummy_update = DummyUpdate(dummy_callback, update.effective_user, update.effective_chat)
            
            # Process the payment
            await handle_payment_made(dummy_update, context, plan)
            return True
        else:
            # Invalid transaction ID format
            await update.message.reply_text(
                "❌ <b>Invalid Transaction ID Format</b>\n\n"
                "Please provide a valid Ethereum transaction hash.\n"
                "It should start with '0x' and be 66 characters long.\n\n"
                "Example: 0x1234...abcd",
                parse_mode=ParseMode.HTML
            )
            return True
    
    return False

async def handle_auto_detect_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle addresses that could be either tokens or wallets
    Automatically detect the type and process accordingly
    """
    address = update.message.text.strip()
    
    # Send initial processing message
    processing_message = await update.message.reply_text(
        "🔍 Analyzing address... This may take a moment."
    )
    
    try:
        # Try to get token data first
        token_data = await get_token_data(address)
        
        if token_data:
            # It's a token address
            context.user_data["expecting"] = "token_address"
            # Create a dummy update with the processing message
            class DummyMessage:
                def __init__(self, text, reply_text_func, reply_func):
                    self.text = text
                    self.reply_text = reply_text_func
                    self.reply = reply_func
            
            dummy_message = DummyMessage(
                address,
                processing_message.edit_text,
                processing_message.reply_text
            )
            
            class DummyUpdate:
                def __init__(self, message, effective_user):
                    self.message = message
                    self.effective_user = effective_user
            
            dummy_update = DummyUpdate(dummy_message, update.effective_user)
            
            # Process as token address
            await handle_expected_input(dummy_update, context)
            return
        
        # If not a token, try as wallet
        wallet_data = await get_wallet_data(address)
        
        if wallet_data:
            # It's a wallet address
            context.user_data["expecting"] = "wallet_address"
            # Create a dummy update with the processing message
            class DummyMessage:
                def __init__(self, text, reply_text_func, reply_func):
                    self.text = text
                    self.reply_text = reply_text_func
                    self.reply = reply_func
            
            dummy_message = DummyMessage(
                address,
                processing_message.edit_text,
                processing_message.reply_text
            )
            
            class DummyUpdate:
                def __init__(self, message, effective_user):
                    self.message = message
                    self.effective_user = effective_user
            
            dummy_update = DummyUpdate(dummy_message, update.effective_user)
            
            # Process as wallet address
            await handle_expected_input(dummy_update, context)
            return
        
        # If we get here, we couldn't identify the address
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            "❓ <b>Address Type Not Detected</b>\n\n"
            f"We couldn't determine if `{address}` is a token or wallet address.\n\n"
            "Please use the specific scan commands:\n"
            "• /scan_token [address] - for token analysis\n"
            "• /scan_wallet [address] - for wallet analysis",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    except Exception as e:
        logging.error(f"Error in handle_auto_detect_address: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            "❌ <b>Error Processing Address</b>\n\n"
            "An error occurred while analyzing the address.\n"
            "Please try again later or use the specific scan commands.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming messages"""
    # Update user activity
    await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    # First check if this is a transaction ID submission
    if await handle_transaction_id(update, context):
        return
    
    # Check if we're expecting specific input
    expecting = context.user_data.get("expecting")
    if expecting:
        if expecting == "auto_detect_address":
            await handle_auto_detect_address(update, context)
        else:
            await handle_expected_input(update, context)
        return
    
    # Handle regular messages
    message_text = update.message.text.strip()
    
    # Process commands without the slash (for convenience)
    if message_text.lower() in ["help", "start", "menu"]:
        await handle_start_menu(update, context)
    elif is_valid_address(message_text):
        # If message is a valid Ethereum address, auto-detect and process
        context.user_data["expecting"] = "auto_detect_address"
        await handle_auto_detect_address(update, context)
    else:
        # Default response for unrecognized messages
        keyboard = [
            [
                InlineKeyboardButton("🔍 Scan Token", callback_data="scan_token"),
                InlineKeyboardButton("👛 Scan Wallet", callback_data="scan_wallet")
            ],
            [InlineKeyboardButton("📋 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 <b>Hello!</b>\n\n"
            "I didn't recognize that as a command or address.\n\n"
            "You can send me a token or wallet address directly, or use the buttons below to access my features.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_command_scan_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan_token command"""
    # Check if user has reached daily limit
    user = await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "token_scan", FREE_TOKEN_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {FREE_TOKEN_SCANS_DAILY} daily token scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check if address was provided with command
    if context.args and len(context.args) > 0:
        # Address provided with command
        address = context.args[0].strip()
        
        if is_valid_address(address):
            # Valid address, process it
            context.user_data["expecting"] = "token_address"
            
            # Create a dummy message with the address
            class DummyMessage:
                def __init__(self, text, reply_text_func):
                    self.text = text
                    self.reply_text = reply_text_func
            
            dummy_message = DummyMessage(
                address,
                update.message.reply_text
            )
            
            class DummyUpdate:
                def __init__(self, message, effective_user):
                    self.message = message
                    self.effective_user = effective_user
            
            dummy_update = DummyUpdate(dummy_message, update.effective_user)
            
            # Process the token address
            await handle_expected_input(dummy_update, context)
        else:
            # Invalid address
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum address or token contract address.\n\n"
                "Example: `/scan_token 0x1234...abcd`",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        # No address provided, prompt user
        await update.message.reply_text(
            "Please send me the token contract address you want to scan.\n\n"
            "Example: `0x1234...abcd`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Set conversation state to expect token address
        context.user_data["expecting"] = "token_address"

async def handle_command_scan_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan_wallet command"""
    # Check if user has reached daily limit
    user = await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, "wallet_scan", FREE_WALLET_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You've used {current_count} out of {FREE_WALLET_SCANS_DAILY} daily wallet scans.\n\n"
            f"Premium users enjoy unlimited scans!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check if address was provided with command
    if context.args and len(context.args) > 0:
        # Address provided with command
        address = context.args[0].strip()
        
        if is_valid_address(address):
            # Valid address, process it
            context.user_data["expecting"] = "wallet_address"
            
            # Create a dummy message with the address
            class DummyMessage:
                def __init__(self, text, reply_text_func):
                    self.text = text
                    self.reply_text = reply_text_func
            
            dummy_message = DummyMessage(
                address,
                update.message.reply_text
            )
            
            class DummyUpdate:
                def __init__(self, message, effective_user):
                    self.message = message
                    self.effective_user = effective_user
            
            dummy_update = DummyUpdate(dummy_message, update.effective_user)
            
            # Process the wallet address
            await handle_expected_input(dummy_update, context)
        else:
            # Invalid address
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum wallet address.\n\n"
                "Example: `/scan_wallet 0x1234...abcd`",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        # No address provided, prompt user
        await update.message.reply_text(
            "Please send me the wallet address you want to scan.\n\n"
            "Example: `0x1234...abcd`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Set conversation state to expect wallet address
        context.user_data["expecting"] = "wallet_address"

async def handle_command_premium_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /premium_help command"""
    user = await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    # Check if user is premium
    if user.is_premium:
        premium_until = user.premium_until.strftime("%d %B %Y") if user.premium_until else "Unknown"
        
        premium_help_text = (
            f"🌟 <b>Crypto DeFi Analyze Premium Features</b>\n\n"
            f"Thank you for being a premium user! Your subscription is active until: <b>{premium_until}</b>\n\n"
            f"<b>Here's what you can do with your premium access:</b>\n\n"
            f"<b>🔍 Advanced Token Analysis:</b>\n"
            f"• Analyze deployer wallet history and risk\n"
            f"• View top holders and whale concentration\n\n"
            f"<b>👛 Wallet Tracking:</b>\n"
            f"• Monitor token for whale movements\n"
            f"• Track wallet for new token deployments\n"
            f"• Track wallet buys & sells\n\n"
            f"<b>💰 Profitability Analysis:</b>\n"
            f"• Find profitable wallets\n"
            f"• Find high net worth wallets\n\n"
            f"<b>📊 Data Export:</b>\n"
            f"• Use the 'Export' buttons to download detailed data\n\n"
            f"<b>Need more help?</b> Contact our support at @SeniorCrypto01"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            premium_help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        # User is not premium, show premium info
        premium_text = (
            "⭐ <b>Upgrade to Crypto DeFi Analyze Premium</b>\n\n"
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
                InlineKeyboardButton("Quarterly Plan", callback_data="premium_quarterly"),
                InlineKeyboardButton("Annual Plan", callback_data="premium_annual")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_command_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /track command with various subcommands"""
    user = await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    # Check if user is premium
    if not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⭐ <b>Premium Feature</b>\n\n"
            "Tracking is only available to premium users.\n\n"
            "💎 Upgrade to premium to unlock all features!",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check if arguments were provided
    if not context.args or len(context.args) == 0:
        # No arguments, show tracking help
        tracking_help_text = (
            "<b>🔔 Tracking Command Help</b>\n\n"
            "Use the /track command with these options:\n\n"
            "• <b>/track [token_address]</b> - Track a token for price movements and whale activity\n"
            "• <b>/track wd [wallet_address]</b> - Track a wallet for new token deployments\n"
            "• <b>/track wbs [wallet_address]</b> - Track a wallet's buy/sell activity\n\n"
            "Examples:\n"
            "• /track 0x1234...abcd\n"
            "• /track wd 0x5678...efgh\n"
            "• /track wbs 0x9012...ijkl"
        )
        
        await update.message.reply_text(
            tracking_help_text,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Process tracking subcommands
    if context.args[0].lower() == "wd" and len(context.args) > 1:
        # Track wallet deployments
        wallet_address = context.args[1].strip()
        
        if is_valid_address(wallet_address):
            # Create tracking subscription for wallet deployments
            from data.models import TrackingSubscription
            from datetime import datetime
            from data.database import save_tracking_subscription, get_tracking_subscription
            
            # Check if subscription already exists
            existing_sub = get_tracking_subscription(user.user_id, "deployer", wallet_address)
            
            if existing_sub and existing_sub.is_active:
                await update.message.reply_text(
                    f"You're already tracking wallet `{wallet_address[:6]}...{wallet_address[-4:]}` for new deployments.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Create new subscription
            subscription = TrackingSubscription(
                user_id=user.user_id,
                tracking_type="deployer",
                target_address=wallet_address,
                is_active=True,
                created_at=datetime.now()
            )
            
            save_tracking_subscription(subscription)
            
            await update.message.reply_text(
                f"✅ Now tracking wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`\n\n"
                f"You will receive notifications when this wallet deploys new tokens.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum wallet address.\n\n"
                "Example: `/track wd 0x1234...abcd`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif context.args[0].lower() == "wbs" and len(context.args) > 1:
        # Track wallet buys/sells
        wallet_address = context.args[1].strip()
        
        if is_valid_address(wallet_address):
            # Create tracking subscription for wallet trades
            from data.models import TrackingSubscription
            from datetime import datetime
            from data.database import save_tracking_subscription, get_tracking_subscription
            
            # Check if subscription already exists
            existing_sub = get_tracking_subscription(user.user_id, "wallet", wallet_address)
            
            if existing_sub and existing_sub.is_active:
                await update.message.reply_text(
                    f"You're already tracking wallet `{wallet_address[:6]}...{wallet_address[-4:]}` for buys/sells.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Create new subscription
            subscription = TrackingSubscription(
                user_id=user.user_id,
                tracking_type="wallet",
                target_address=wallet_address,
                is_active=True,
                created_at=datetime.now()
            )
            
            save_tracking_subscription(subscription)
            
            await update.message.reply_text(
                f"✅ Now tracking wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`\n\n"
                f"You will receive notifications when this wallet makes significant trades.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum wallet address.\n\n"
                "Example: `/track wbs 0x1234...abcd`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    else:
        # Assume first argument is a token address
        token_address = context.args[0].strip()
        
        if is_valid_address(token_address):
            # Create tracking subscription for token
            from data.models import TrackingSubscription
            from datetime import datetime
            from data.database import save_tracking_subscription, get_tracking_subscription, get_token_data
            
            # Check if subscription already exists
            existing_sub = get_tracking_subscription(user.user_id, "token", token_address)
            
            if existing_sub and existing_sub.is_active:
                await update.message.reply_text(
                    f"You're already tracking token `{token_address[:6]}...{token_address[-4:]}`.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Create new subscription
            subscription = TrackingSubscription(
                user_id=user.user_id,
                tracking_type="token",
                target_address=token_address,
                is_active=True,
                created_at=datetime.now()
            )
            
            save_tracking_subscription(subscription)
            
            # Get token data for name
            token_data = await get_token_data(token_address)
            token_name = token_data.get('name', 'Unknown Token') if token_data else 'this token'
            
            await update.message.reply_text(
                f"✅ Now tracking token: {token_name}\n\n"
                f"Contract: `{token_address[:6]}...{token_address[-4:]}`\n\n"
                f"You will receive notifications for significant price movements, "
                f"whale transactions, and other important events.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "⚠️ Please provide a valid Ethereum token address.\n\n"
                "Example: `/track 0x1234...abcd`",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_command_my_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /my_tracking command to show user's active tracking subscriptions"""
    user = await get_or_create_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )
    
    # Get user's tracking subscriptions
    from data.database import get_user_tracking_subscriptions
    subscriptions = get_user_tracking_subscriptions(user.user_id)
    
    if not subscriptions:
        await update.message.reply_text(
            "📭 <b>No Active Tracking Subscriptions</b>\n\n"
            "You are not currently tracking any tokens or wallets.\n\n"
            "Use the /track command to start tracking.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Group subscriptions by type
    token_subs = [sub for sub in subscriptions if sub.tracking_type == "token"]
    wallet_subs = [sub for sub in subscriptions if sub.tracking_type == "wallet"]
    deployer_subs = [sub for sub in subscriptions if sub.tracking_type == "deployer"]
    
    # Format the response
    response = "<b>🔔 Your Active Tracking Subscriptions</b>\n\n"
    
    if token_subs:
        response += "<b>📊 Tokens:</b>\n"
        for i, sub in enumerate(token_subs, 1):
            response += f"{i}. `{sub.target_address[:6]}...{sub.target_address[-4:]}`\n"
        response += "\n"
    
    if wallet_subs:
        response += "<b>👛 Wallets (Buys/Sells):</b>\n"
        for i, sub in enumerate(wallet_subs, 1):
            response += f"{i}. `{sub.target_address[:6]}...{sub.target_address[-4:]}`\n"
        response += "\n"
    
    if deployer_subs:
        response += "<b>🏗️ Deployer Wallets:</b>\n"
        for i, sub in enumerate(deployer_subs, 1):
            response += f"{i}. `{sub.target_address[:6]}...{sub.target_address[-4:]}`\n"
        response += "\n"
    
    response += "To stop tracking, use /untrack [address]"
    
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.HTML
    )

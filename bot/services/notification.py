import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import random

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from .blockchain import get_token_info, get_wallet_info
from data.models import TrackingSubscription, User
from data.database import get_user, get_user_tracking_subscriptions

# Initialize bot instance
# This would be properly initialized in the main application
bot = None

def set_bot(bot_instance: Bot) -> None:
    """Set the bot instance for sending notifications"""
    global bot
    bot = bot_instance

async def send_notification(user_id: int, message: str, parse_mode: Optional[str] = ParseMode.MARKDOWN, reply_markup=None) -> bool:
    """Send a notification to a user"""
    if not bot:
        logging.error("Bot instance not set for notifications")
        return False
        
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        logging.error(f"Error sending notification to user {user_id}: {e}")
        return False

async def process_tracking_alerts() -> None:
    """Process all tracking subscriptions and send alerts if needed"""
    from data.database import get_all_active_tracking_subscriptions
    
    try:
        # Get all active tracking subscriptions
        subscriptions = get_all_active_tracking_subscriptions()
        
        for subscription in subscriptions:
            user = get_user(subscription.user_id)
            if not user or not user.is_premium:
                continue
                
            # Process based on tracking type
            if subscription.tracking_type == "token":
                await process_token_tracking(user, subscription)
            elif subscription.tracking_type == "wallet":
                await process_wallet_tracking(user, subscription)
            elif subscription.tracking_type == "deployer":
                await process_deployer_tracking(user, subscription)
    except Exception as e:
        logging.error(f"Error processing tracking alerts: {e}")

async def process_token_tracking(user: User, subscription: TrackingSubscription) -> None:
    """Process token tracking and send alerts if needed"""
    token_address = subscription.target_address
    
    try:
        # Get token info
        token_info = await get_token_info(token_address)
        if not token_info:
            return
            
        # Check for significant price changes
        last_check = subscription.last_check or datetime.now() - timedelta(days=1)
        
        # This would be replaced with actual historical data comparison
        # For now, we'll simulate alerts based on random conditions
        if datetime.now() - last_check > timedelta(hours=6):
            # Simulate price change
            price_change_pct = round((token_info.get("current_price", 0) / 
                                     subscription.last_data.get("price", token_info.get("current_price", 0)) - 1) * 100, 2)
            
            # Alert on significant price changes
            if abs(price_change_pct) > 10:
                direction = "increased" if price_change_pct > 0 else "decreased"
                
                # Create inline keyboard for actions
                keyboard = [
                    [
                        InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}"),
                        InlineKeyboardButton("Stop Tracking", callback_data=f"stop_track_token_{token_address}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await send_notification(
                    user.user_id,
                    f"🚨 *Token Alert*\n\n"
                    f"The price of {token_info.get('name', 'your tracked token')} ({token_info.get('symbol', '???')}) "
                    f"has {direction} by {abs(price_change_pct)}% in the last 6 hours.\n\n"
                    f"Current price: ${token_info.get('current_price', 0)}\n"
                    f"Current market cap: ${token_info.get('current_market_cap', 0)}",
                    reply_markup=reply_markup
                )
            
            # Update last check and data
            from data.database import update_tracking_subscription_data
            update_tracking_subscription_data(
                subscription.user_id,
                subscription.tracking_type,
                subscription.target_address,
                {"price": token_info.get("current_price", 0)}
            )
    except Exception as e:
        logging.error(f"Error processing token tracking for {token_address}: {e}")

async def process_wallet_tracking(user: User, subscription: TrackingSubscription) -> None:
    """Process wallet tracking and send alerts if needed"""
    wallet_address = subscription.target_address
    
    try:
        # Get wallet info
        wallet_info = await get_wallet_info(wallet_address)
        if not wallet_info:
            return
            
        # Check for significant transactions or holdings changes
        last_check = subscription.last_check or datetime.now() - timedelta(days=1)
        
        # This would be replaced with actual transaction monitoring
        # For now, we'll simulate alerts based on random conditions
        if datetime.now() - last_check > timedelta(hours=12):
            # Simulate transaction
            transaction_happened = datetime.now().hour % 4 == 0  # Random condition
            
            if transaction_happened:
                # Simulate transaction details
                token_symbol = f"TOKEN{datetime.now().minute % 10}"
                token_address = f"0x{datetime.now().minute:02d}token{wallet_address[-4:]}"
                action = "bought" if datetime.now().minute % 2 == 0 else "sold"
                amount = round(random.uniform(1000, 100000), 2)
                
                # Create inline keyboard for actions
                keyboard = [
                    [
                        InlineKeyboardButton("View Wallet", callback_data=f"view_wallet_{wallet_address}"),
                        InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}")
                    ],
                    [
                        InlineKeyboardButton("Stop Tracking", callback_data=f"stop_track_wallet_{wallet_address}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await send_notification(
                    user.user_id,
                    f"👁️ *Wallet Activity Alert*\n\n"
                    f"The wallet you're tracking (`{wallet_address[:6]}...{wallet_address[-4:]}`) "
                    f"has {action} {amount} {token_symbol}.\n\n"
                    f"Transaction time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup
                )
            
            # Update last check
            from data.database import update_tracking_subscription_last_check
            update_tracking_subscription_last_check(
                subscription.user_id,
                subscription.tracking_type,
                subscription.target_address
            )
    except Exception as e:
        logging.error(f"Error processing wallet tracking for {wallet_address}: {e}")

async def process_deployer_tracking(user: User, subscription: TrackingSubscription) -> None:
    """Process deployer tracking and send alerts if needed"""
    deployer_address = subscription.target_address
    
    try:
        # Get deployer info (using wallet info for now)
        deployer_info = await get_wallet_info(deployer_address)
        if not deployer_info:
            return
            
        # Check for new token deployments
        last_check = subscription.last_check or datetime.now() - timedelta(days=1)
        
        # This would be replaced with actual deployment monitoring
        # For now, we'll simulate alerts based on random conditions
        if datetime.now() - last_check > timedelta(hours=24):
            # Simulate new deployment
            new_deployment = datetime.now().day % 3 == 0  # Random condition
            
            if new_deployment:
                # Simulate token details
                token_name = f"New Token {datetime.now().day}"
                token_symbol = f"NTKN{datetime.now().day}"
                token_address = f"0x{datetime.now().day:02d}newtoken{deployer_address[-4:]}"
                
                # Create inline keyboard for actions
                keyboard = [
                    [
                        InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}"),
                        InlineKeyboardButton("Track This Token", callback_data=f"track_token_{token_address}")
                    ],
                    [
                        InlineKeyboardButton("Stop Tracking Deployer", callback_data=f"stop_track_deployer_{deployer_address}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await send_notification(
                    user.user_id,
                    f"🚀 *New Token Deployment Alert*\n\n"
                    f"The deployer wallet you're tracking (`{deployer_address[:6]}...{deployer_address[-4:]}`) "
                    f"has deployed a new token:\n\n"
                    f"Name: {token_name}\n"
                    f"Symbol: {token_symbol}\n"
                    f"Address: `{token_address}`\n\n"
                    f"Deployment time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup
                )
            
            # Update last check
            from data.database import update_tracking_subscription_last_check
            update_tracking_subscription_last_check(
                subscription.user_id,
                subscription.tracking_type,
                subscription.target_address
            )
    except Exception as e:
        logging.error(f"Error processing deployer tracking for {deployer_address}: {e}")

async def send_price_alert(user_id: int, token_address: str, price_change_pct: float) -> None:
    """Send a price alert notification for a tracked token"""
    try:
        token_info = await get_token_info(token_address)
        if not token_info:
            return
            
        direction = "increased" if price_change_pct > 0 else "decreased"
        
        # Create inline keyboard for actions
        keyboard = [
            [
                InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}"),
                InlineKeyboardButton("Stop Alerts", callback_data=f"stop_price_alerts_{token_address}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_notification(
            user_id,
            f"💰 *Price Alert*\n\n"
            f"{token_info.get('name', 'Token')} ({token_info.get('symbol', '???')}) "
            f"has {direction} by {abs(price_change_pct)}%.\n\n"
            f"Current price: ${token_info.get('current_price', 0)}\n"
            f"24h volume: ${token_info.get('volume_24h', 'N/A')}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending price alert for {token_address}: {e}")

async def send_whale_movement_alert(user_id: int, token_address: str, wallet_address: str, amount: float, action: str) -> None:
    """Send a whale movement alert for a tracked token"""
    try:
        token_info = await get_token_info(token_address)
        if not token_info:
            return
            
        # Create inline keyboard for actions
        keyboard = [
            [
                InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}"),
                InlineKeyboardButton("View Wallet", callback_data=f"view_wallet_{wallet_address}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        value = amount * token_info.get('current_price', 0)
        
        await send_notification(
            user_id,
            f"🐋 *Whale Movement Alert*\n\n"
            f"A whale has {action} a large amount of {token_info.get('name', 'Token')} ({token_info.get('symbol', '???')}).\n\n"
            f"Wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`\n"
            f"Amount: {amount:,.2f} tokens (${value:,.2f})\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending whale movement alert for {token_address}: {e}")

async def send_liquidity_change_alert(user_id: int, token_address: str, liquidity_change_pct: float) -> None:
    """Send a liquidity change alert for a tracked token"""
    try:
        token_info = await get_token_info(token_address)
        if not token_info:
            return
            
        direction = "increased" if liquidity_change_pct > 0 else "decreased"
        risk_level = "Low" if liquidity_change_pct > 0 else ("High" if liquidity_change_pct < -20 else "Medium")
        
        # Create inline keyboard for actions
        keyboard = [
            [InlineKeyboardButton("View Token", callback_data=f"view_token_{token_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_notification(
            user_id,
            f"💧 *Liquidity Change Alert*\n\n"
            f"The liquidity for {token_info.get('name', 'Token')} ({token_info.get('symbol', '???')}) "
            f"has {direction} by {abs(liquidity_change_pct)}%.\n\n"
            f"Risk level: {risk_level}\n"
            f"Current liquidity: ${token_info.get('liquidity', 'N/A')}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending liquidity change alert for {token_address}: {e}")

async def send_premium_expiration_reminder(user: User) -> None:
    """Send a reminder that premium subscription is about to expire"""
    try:
        if not user.is_premium or not user.premium_until:
            return
            
        days_left = (user.premium_until - datetime.now()).days
        
        if days_left in [7, 3, 1]:
            # Create inline keyboard for renewal
            keyboard = [
                [InlineKeyboardButton("Renew Premium", callback_data="premium_renew")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_notification(
                user.user_id,
                f"⚠️ *Premium Expiration Reminder*\n\n"
                f"Your DeFi-Scope Bot premium subscription will expire in {days_left} day{'s' if days_left > 1 else ''}.\n\n"
                f"Renew now to maintain access to all premium features!",
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error sending premium expiration reminder to user {user.user_id}: {e}")

async def send_premium_expired_notification(user: User) -> None:
    """Send a notification that premium subscription has expired"""
    try:
        # Create inline keyboard for renewal
        keyboard = [
            [InlineKeyboardButton("Renew Premium", callback_data="premium_renew")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_notification(
            user.user_id,
            f"⏰ *Premium Subscription Expired*\n\n"
            f"Your DeFi-Scope Bot premium subscription has expired.\n\n"
            f"You'll no longer have access to premium features such as:\n"
            f"• Unlimited token and wallet scans\n"
            f"• Tracking tokens, wallets, and deployers\n"
            f"• Access to deployer wallet analysis\n"
            f"• And more...\n\n"
            f"Renew now to continue enjoying all premium benefits!",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending premium expired notification to user {user.user_id}: {e}")

async def send_tracking_confirmation(user_id: int, tracking_type: str, target_address: str) -> None:
    """Send a confirmation that tracking has been set up"""
    try:
        # Get name based on tracking type
        name = target_address
        if tracking_type == "token":
            token_info = await get_token_info(target_address)
            if token_info:
                name = f"{token_info.get('name', 'Unknown Token')} ({token_info.get('symbol', 'N/A')})"
        
        # Create inline keyboard for actions
        keyboard = [
            [InlineKeyboardButton(f"View {tracking_type.capitalize()}", callback_data=f"view_{tracking_type}_{target_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_notification(
            user_id,
            f"✅ *Tracking Confirmed*\n\n"
            f"You are now tracking this {tracking_type}:\n"
            f"`{target_address[:6]}...{target_address[-4:]}`\n\n"
            f"You will receive notifications for significant events related to this {tracking_type}.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending tracking confirmation to user {user_id}: {e}")

async def send_tracking_stopped_confirmation(user_id: int, tracking_type: str, target_address: str) -> None:
    """Send a confirmation that tracking has been stopped"""
    try:
        await send_notification(
            user_id,
            f"🛑 *Tracking Stopped*\n\n"
            f"You are no longer tracking this {tracking_type}:\n"
            f"`{target_address[:6]}...{target_address[-4:]}`\n\n"
            f"You will not receive any more notifications for this {tracking_type}."
        )
    except Exception as e:
        logging.error(f"Error sending tracking stopped confirmation to user {user_id}: {e}")

async def send_premium_welcome(user_id: int, plan_type: str, duration_days: int) -> None:
    """Send a welcome message after user upgrades to premium"""
    try:
        expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime("%d %B %Y")
        
        await send_notification(
            user_id,
            f"🌟 *Welcome to DeFi-Scope Premium!*\n\n"
            f"Thank you for upgrading to our {plan_type} plan.\n\n"
            f"Your premium subscription is now active and will expire on *{expiry_date}*.\n\n"
            f"You now have access to all premium features:\n"
            f"• Unlimited token and wallet scans\n"
            f"• Tracking tokens, wallets, and deployers\n"
            f"• Access to deployer wallet analysis\n"
            f"• View top holders of any token\n"
            f"• Access to profitable wallets database\n"
            f"• High net worth wallet monitoring\n"
            f"• Priority support\n\n"
            f"Enjoy your premium experience!"
        )
    except Exception as e:
        logging.error(f"Error sending premium welcome to user {user_id}: {e}")

async def send_daily_summary(user: User) -> None:
    """Send a daily summary of tracked assets to premium users"""
    try:
        if not user.is_premium:
            return
            
        # Get user's tracking subscriptions
        from data.database import get_user_tracking_subscriptions
        subscriptions = get_user_tracking_subscriptions(user.user_id)
        
        if not subscriptions:
            return
            
        # Count by type
        token_count = sum(1 for sub in subscriptions if sub.tracking_type == "token")
        wallet_count = sum(1 for sub in subscriptions if sub.tracking_type == "wallet")
        deployer_count = sum(1 for sub in subscriptions if sub.tracking_type == "deployer")
        
        # Create summary message
        summary = f"📊 *Your Daily DeFi Summary*\n\n"
        summary += f"Date: {datetime.now().strftime('%d %B %Y')}\n\n"
        
        # Add tracking stats
        summary += f"*Your Tracking Stats:*\n"
        summary += f"• Tokens tracked: {token_count}\n"
        summary += f"• Wallets tracked: {wallet_count}\n"
        summary += f"• Deployers tracked: {deployer_count}\n\n"
        
        # Add market overview (simulated)
        summary += f"*Market Overview:*\n"
        summary += f"• ETH Price: ${random.uniform(1500, 3000):.2f}\n"
        summary += f"• Market Sentiment: {random.choice(['Bullish', 'Neutral', 'Bearish'])}\n"
        summary += f"• DeFi TVL: ${random.uniform(10, 100):.2f}B\n\n"
        
        # Add notable events if any tracked tokens had significant changes
        if token_count > 0:
            summary += f"*Notable Events:*\n"
            # Simulate some events
            if random.random() > 0.5:
                summary += f"• One of your tracked tokens had a price increase of {random.uniform(10, 50):.1f}%\n"
            if random.random() > 0.7:
                summary += f"• Whale movement detected in {random.randint(1, token_count)} of your tracked tokens\n"
        
        # Create inline keyboard for actions
        keyboard = [
            [
                InlineKeyboardButton("View All Tracked", callback_data="view_all_tracked"),
                InlineKeyboardButton("Market Analysis", callback_data="market_analysis")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_notification(
            user.user_id,
            summary,
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Error sending daily summary to user {user.user_id}: {e}")

async def check_and_send_premium_reminders() -> None:
    """Check for users with expiring premium and send reminders"""
    try:
        from data.database import get_users_with_expiring_premium
        
        # Get users whose premium is expiring soon (7, 3, or 1 day)
        expiring_users = get_users_with_expiring_premium([7, 3, 1])
        
        for user in expiring_users:
            await send_premium_expiration_reminder(user)
            
        # Get users whose premium has expired today
        expired_users = get_users_with_expiring_premium([0])
        
        for user in expired_users:
            await send_premium_expired_notification(user)
            
            # Update user's premium status
            from data.database import set_premium_status
            set_premium_status(user.user_id, False)
    except Exception as e:
        logging.error(f"Error checking and sending premium reminders: {e}")

async def send_new_feature_announcement(feature_name: str, feature_description: str) -> None:
    """Send an announcement about a new feature to all users"""
    try:
        from data.database import get_all_users
        
        users = get_all_users()
        
        # Create inline keyboard for actions
        keyboard = [
            [InlineKeyboardButton("Try It Now", callback_data=f"try_feature_{feature_name.lower().replace(' ', '_')}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for user in users:
            await send_notification(
                user.user_id,
                f"🎉 *New Feature Announcement*\n\n"
                f"We've just launched a new feature: *{feature_name}*\n\n"
                f"{feature_description}\n\n"
                f"Try it out now!",
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error sending new feature announcement: {e}")

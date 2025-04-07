import asyncio
import logging
from datetime import datetime
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder

from config import TELEGRAM_TOKEN
from data.database import get_all_active_tracking_subscriptions

async def send_tracking_notification(user_id: int, message: str) -> None:
    """
    Send a notification to a user about a tracked event
    
    Args:
        user_id: The Telegram user ID to send the notification to
        message: The message text to send (supports HTML formatting)
    """
    try:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        await application.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Notification sent to user {user_id}")
    except Exception as e:
        logging.error(f"Failed to send notification to user {user_id}: {e}")

async def send_bulk_notifications(user_ids: list, message: str) -> None:
    """
    Send the same notification to multiple users
    
    Args:
        user_ids: List of Telegram user IDs to send notifications to
        message: The message text to send (supports HTML formatting)
    """
    for user_id in user_ids:
        await send_tracking_notification(user_id, message)
        # Add a small delay to avoid hitting Telegram API rate limits
        await asyncio.sleep(0.05)

def format_wallet_activity_notification(wallet_address: str, tx_data: dict) -> str:
    """
    Format a notification message for wallet activity
    
    Args:
        wallet_address: The wallet address that performed the activity
        tx_data: Transaction data dictionary
        
    Returns:
        Formatted HTML message
    """
    token_name = tx_data.get('token_name', 'Unknown Token')
    action = '🟢 Buy' if tx_data.get('is_buy', False) else '🔴 Sell'
    
    return (
        f"🚨 <b>Wallet Activity Alert</b>\n\n"
        f"The wallet you're tracking has made a transaction:\n"
        f"Wallet: <code>{wallet_address[:6]}...{wallet_address[-4:]}</code>\n"
        f"Action: {action}\n"
        f"Token: {token_name}\n"
        f"Amount: {tx_data.get('amount', 'Unknown')} tokens\n"
        f"Value: ${tx_data.get('value_usd', 'Unknown')}\n"
        f"Time: {tx_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
    )

def format_token_deployment_notification(deployer_address: str, contract_address: str, timestamp: str) -> str:
    """
    Format a notification message for token deployment
    
    Args:
        deployer_address: The wallet address that deployed the token
        contract_address: The address of the deployed token contract
        timestamp: When the deployment occurred
        
    Returns:
        Formatted HTML message
    """
    return (
        f"🚨 <b>Token Deployment Alert</b>\n\n"
        f"The wallet you're tracking has deployed a new token:\n"
        f"Deployer: <code>{deployer_address[:6]}...{deployer_address[-4:]}</code>\n"
        f"Token Address: <code>{contract_address}</code>\n"
        f"Time: {timestamp}"
    )

def format_profitable_wallet_notification(wallet_address: str, token_name: str, tx_data: dict) -> str:
    """
    Format a notification message for profitable wallet activity
    
    Args:
        wallet_address: The wallet address that performed the activity
        token_name: The name of the token involved
        tx_data: Transaction data dictionary
        
    Returns:
        Formatted HTML message
    """
    action = '🟢 Buy' if tx_data.get('is_buy', False) else '🔴 Sell'
    
    return (
        f"🚨 <b>Profitable Wallet Alert</b>\n\n"
        f"A profitable wallet for {token_name} has made a transaction:\n"
        f"Wallet: <code>{wallet_address[:6]}...{wallet_address[-4:]}</code>\n"
        f"Action: {action}\n"
        f"Amount: {tx_data.get('amount', 'Unknown')} tokens\n"
        f"Value: ${tx_data.get('value_usd', 'Unknown')}\n"
        f"Time: {tx_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
    )

import random
import logging
from datetime import datetime, timedelta

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

async def handle_token_analysis_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    analysis_type: str,
    get_data_func,
    format_response_func,
    scan_count_type: str,
    processing_message_text: str,
    error_message_text: str,
    no_data_message_text: str
) -> None:
    """
    Generic handler for token analysis inputs
    
    Args:
        update: The update object
        context: The context object
        analysis_type: Type of analysis being performed (for logging)
        get_data_func: Function to get the data (takes token_address and chain)
        format_response_func: Function to format the response (takes data and token_data)
        scan_count_type: Type of scan to increment count for
        processing_message_text: Text to show while processing
        error_message_text: Text to show on error
        no_data_message_text: Text to show when no data is found
    """
    token_address = update.message.text.strip()
    chain = context.user_data.get("default_network")
    print(f"Selected chain: {chain}")
    
    # Validate address
    if not await is_valid_token_contract(token_address, chain):
        # Add back button to validation error message
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ Something went wrong.⚠️ Please provide a valid token contract address for {chain}.",
            reply_markup=reply_markup
        )
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(processing_message_text)
    
    try:
        # Get data
        token_info = await get_token_info(token_address, chain)
        data = await get_data_func(token_address, chain)
        
        if not data or not token_info:
            # Add back button when no data is found
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                no_data_message_text,
                reply_markup=reply_markup
            )
            return
        
        # Format the response
        response, keyboard = format_response_func(data, token_info, token_address)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success = False
        try:
            # Try to edit the current message
            await processing_message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            success = True
        except Exception as e:
            logging.error(f"Error in handle_{analysis_type}: {e}")
            # If editing fails, send a new message
            await update.message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            success = True
            # Delete the original message if possible
            try:
                await processing_message.delete()
            except:
                pass
        
        # Only increment scan count if we successfully displayed data
        if success:
            # Get the user directly from the message update
            user_id = update.effective_user.id
            user = get_user(user_id)
            if not user:
                # Create user if not exists
                user = User(user_id=user_id, username=update.effective_user.username)
                # Save user to database if needed
            
            await increment_scan_count(user_id, scan_count_type)
    
    except Exception as e:
        logging.error(f"Error in handle_expected_input ({analysis_type}): {e}")
        
        # Add back button to exception error message
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            error_message_text,
            reply_markup=reply_markup
        )

async def get_token_info(token_address: str, chain: str = "eth") -> Optional[Dict[str, Any]]:
    """Get detailed information about a token"""
    if not await is_valid_token_contract(token_address, chain):
        return None
    
    try:      
        # Get the appropriate web3 provider based on chain
        w3 = get_web3_provider(chain)
        
        # ERC20 ABI for basic token information
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
        ]
        
        # Create contract instance
        contract = w3.eth.contract(address=token_address, abi=abi)
        
        # Get basic token information
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        total_supply = contract.functions.totalSupply().call() / (10 ** decimals)
        
        # Simulate historical data
        return {
            "address": token_address,
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "total_supply": total_supply
        }
    except Exception as e:
        logging.error(f"Error getting token info on {chain}: {e}")
        return None

def format_first_buyers_response(first_buyers: List[Dict[str, Any]], 
                                token_data: Dict[str, Any], 
                                token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for first buyers analysis
    
    Args:
        first_buyers: List of first buyer data
        token_data: Token information
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    response = (
        f"🛒 <b>First Buyers Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
    )
    
    for i, buyer in enumerate(first_buyers[:10], 1):
        response += (
            f"{i}. `{buyer['address'][:6]}...{buyer['address'][-4:]}`\n"
            f"   Buy Amount: {buyer.get('buy_amount', 'N/A')} tokens\n"
            f"   Buy Value: ${buyer.get('buy_value', 'N/A')}\n"
            f"   Current PNL: {buyer.get('pnl', 'N/A')}%\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_profitable_wallets_response(profitable_wallets: List[Dict[str, Any]], 
                                      token_data: Dict[str, Any], 
                                      token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for most profitable wallets analysis
    
    Args:
        profitable_wallets: List of profitable wallet data
        token_data: Token information
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    response = (
        f"💰 <b>Most Profitable Wallets for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
    )
    
    for i, wallet in enumerate(profitable_wallets[:10], 1):
        response += (
            f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Buy Amount: {wallet.get('buy_amount', 'N/A')} tokens\n"
            f"   Sell Amount: {wallet.get('sell_amount', 'N/A')} tokens\n"
            f"   Profit: ${wallet.get('profit', 'N/A')}\n"
            f"   ROI: {wallet.get('roi', 'N/A')}%\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_ath_response(token_data: Dict[str, Any], token_data_again: Dict[str, Any], token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for ATH analysis
    
    Args:
        token_data: Token information (first parameter from handle_token_analysis_input)
        token_data_again: Same token information (second parameter from handle_token_analysis_input)
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    # Note: token_data and token_data_again are the same in this case
    # We're using this signature to match the expected format for handle_token_analysis_input
    
    # Calculate percentage from ATH
    current_mc = token_data.get('current_market_cap', 0)
    ath_mc = token_data.get('ath_market_cap', 0)
    
    if current_mc > 0 and ath_mc > 0:
        percent_from_ath = round((current_mc / ath_mc) * 100, 2)
    else:
        percent_from_ath = "N/A"
    
    response = (
        f"📈 <b>ATH Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
        f"<b>Current Status:</b>\n"
        f"• Current Price: ${token_data.get('current_price', 'N/A')}\n"
        f"• Current Market Cap: ${format_number(token_data.get('current_market_cap', 'N/A'))}\n"
        f"• Holders: {format_number(token_data.get('holders_count', 'N/A'))}\n\n"
        f"<b>All-Time High:</b>\n"
        f"• ATH Price: ${token_data.get('ath_price', 'N/A')}\n"
        f"• ATH Market Cap: ${format_number(token_data.get('ath_market_cap', 'N/A'))}\n"
        f"• ATH Date: {token_data.get('ath_date', 'N/A')}\n"
        f"• Current % of ATH: {percent_from_ath}%\n\n"
        f"<b>Token Info:</b>\n"
        f"• Launch Date: {token_data.get('launch_date', 'N/A')}\n"
        f"• Liquidity: ${format_number(token_data.get('liquidity', 'N/A'))}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_number(num):
    """Format a number with commas for thousands"""
    if isinstance(num, (int, float)):
        return f"{num:,}"
    return num

def format_deployer_wallet_scan_response(deployer_data: Dict[str, Any], 
                                        token_data: Dict[str, Any], 
                                        token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for deployer wallet scan
    
    Args:
        deployer_data: Deployer wallet data
        token_data: Token information
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    # Get deployer address
    deployer_address = deployer_data.get("deployer_address", "Unknown")
    
    response = (
        f"🔎 <b>Deployer Wallet Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n"
        f"Deployer: `{deployer_address}`\n\n"
        
        f"<b>Deployer Profile:</b>\n"
        f"• Tokens Deployed: {deployer_data.get('tokens_deployed', 'N/A')}\n"
        f"• First Deployment: {deployer_data.get('first_deployment_date', 'N/A')}\n"
        f"• Last Deployment: {deployer_data.get('last_deployment_date', 'N/A')}\n"
        f"• Success Rate: {deployer_data.get('success_rate', 'N/A')}%\n"
        f"• Avg. ROI: {deployer_data.get('avg_roi', 'N/A')}%\n"
        f"• Rugpull History: {deployer_data.get('rugpull_count', 'N/A')} tokens\n"
        f"• Risk Assessment: <b>{deployer_data.get('risk_level', 'Unknown')}</b>\n\n"
        
        f"<b>Other Tokens by This Deployer:</b>\n"
    )
    
    # Add deployed tokens info
    deployed_tokens = deployer_data.get("deployed_tokens", [])
    for i, token in enumerate(deployed_tokens[:5], 1):  # Show top 5 tokens
        response += (
            f"{i}. {token.get('name', 'Unknown')} ({token.get('symbol', 'N/A')})\n"
            f"   Deploy Date: {token.get('deploy_date', 'N/A')}\n"
            f"   ATH Market Cap: ${format_number(token.get('ath_market_cap', 'N/A'))}\n"
            f"   X-Multiplier: {token.get('x_multiplier', 'N/A')}\n"
            f"   Status: {token.get('status', 'Unknown')}\n\n"
        )
    
    # Add note if there are more tokens
    if len(deployed_tokens) > 5:
        response += f"<i>+ {len(deployed_tokens) - 5} more tokens</i>\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_top_holders_response(top_holders: List[Dict[str, Any]], 
                               token_data: Dict[str, Any], 
                               token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for top holders analysis
    
    Args:
        top_holders: List of top holder data
        token_data: Token information
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    response = (
        f"🐳 <b>Top Holders Analysis for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
    )
    
    # Add summary information
    total_percentage = sum(holder.get('percentage', 0) for holder in top_holders)
    response += (
        f"<b>Summary:</b>\n"
        f"• Top 10 holders control: {round(total_percentage, 2)}% of supply\n"
        f"• Total holders: {format_number(token_data.get('holders_count', 'N/A'))}\n\n"
        f"<b>Top Holders:</b>\n"
    )
    
    # Add top holders information
    for holder in top_holders:
        wallet_type = holder.get('wallet_type', 'Unknown')
        exchange_info = f" ({holder.get('exchange_name', '')})" if wallet_type == "Exchange" else ""
        
        response += (
            f"{holder.get('rank', '?')}. `{holder['address'][:6]}...{holder['address'][-4:]}`{exchange_info}\n"
            f"   Tokens: {format_number(holder.get('token_amount', 'N/A'))} ({holder.get('percentage', 'N/A')}%)\n"
            f"   Value: ${format_number(holder.get('usd_value', 'N/A'))}\n"
            f"   Holding since: {holder.get('holding_since', 'N/A')}\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_high_net_worth_holders_response(high_net_worth_holders: List[Dict[str, Any]], 
                                          token_data: Dict[str, Any], 
                                          token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for high net worth holders analysis
    
    Args:
        high_net_worth_holders: List of high net worth holder data
        token_data: Token information
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    response = (
        f"💰 <b>High Net Worth Holders for {token_data.get('name', 'Unknown Token')} ({token_data.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
        f"<b>Holders with minimum $10,000 worth of tokens:</b>\n\n"
    )
    
    # Add high net worth holders information
    for i, holder in enumerate(high_net_worth_holders, 1):
        response += (
            f"{i}. `{holder['address'][:6]}...{holder['address'][-4:]}`\n"
            f"   Tokens: {format_number(holder.get('token_amount', 'N/A'))}\n"
            f"   Value: ${format_number(holder.get('usd_value', 'N/A'))}\n"
            f"   Portfolio: {holder.get('portfolio_size', 'N/A')} tokens\n"
            f"   Avg. holding time: {holder.get('avg_holding_time', 'N/A')} days\n"
            f"   Success rate: {holder.get('success_rate', 'N/A')}%\n"
            f"   Avg. ROI: {holder.get('avg_roi', 'N/A')}%\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard


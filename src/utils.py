import random
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from data.models import User
from config import FREE_WALLET_SCANS_DAILY

from services.blockchain import * 
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
        f"🎉 <b>Welcome to Crypto DeFi Analyze Premium!</b>\n\n"
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

# token analysis input 
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
    selected_chain = context.user_data.get("default_network")
    
    # Validate address
    if not await is_valid_token_contract(token_address, selected_chain):
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ Something went wrong.⚠️ Please provide a valid token contract address for {selected_chain}.",
            reply_markup=reply_markup
        )
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(processing_message_text)
    
    try:
        # Get data
        token_info = await get_token_info(token_address, selected_chain)
        data = await get_data_func(token_address, selected_chain)
        
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
            f"{i}. `{buyer['maker']}`\n"
            f"   Buy Amount: {buyer.get('base_amount', 'N/A')} tokens\n"
            f"   Buy Value: ${buyer.get('amount_usd', 'N/A')}\n"
            f"   Current PNL: {buyer.get('realized_profit', 'N/A')}%\n\n"
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
        # Format the trader ID (wallet address)
        trader_id = wallet.get('trader_id', wallet.get('address', 'Unknown'))
        
        # Calculate ROI percentage
        total_buy_usd = wallet.get('total_buy_usd', 0)
        roi_percentage = 0
        if total_buy_usd > 0:
            roi_percentage = round((wallet.get('total_profit', 0) / total_buy_usd) * 100, 2)
        
        response += (
            f"{i}. `{trader_id[:6]}...{trader_id[-4:]}`\n"
            f"   Total Trades: {wallet.get('total_trades', 'N/A')}\n"
            f"   Win Rate: {round(wallet.get('win_rate', 0) * 100, 2)}%\n"
            f"   Buy Amount: ${wallet.get('total_buy_usd', 'N/A'):,.2f}\n"
            f"   Sell Amount: ${wallet.get('total_sell_usd', 'N/A'):,.2f}\n"
            f"   Profit: ${wallet.get('total_profit', 'N/A'):,.2f}\n"
            f"   ROI: {roi_percentage}%\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="token_analysis")]
    ]
    
    return response, keyboard

def format_ath_response(ath_data: Dict[str, Any], token_info: Dict[str, Any], token_address: str) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    """
    Format the response for ATH analysis
    
    Args:
        ath_data: ATH information (first parameter from handle_token_analysis_input)
        token_info: token information (second parameter from handle_token_analysis_input)
        token_address: The token address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    # We're using this signature to match the expected format for handle_token_analysis_input
    
    # Calculate percentage from ATH
    cur_mcap = ath_data.get('cur_mcap', 0)
    ath_mcap = ath_data.get('ath_mcap', 0)
    
    if cur_mcap > 0 and ath_mcap > 0:
        percent_from_ath = round((cur_mcap / ath_mcap) * 100, 2)
    else:
        percent_from_ath = "N/A"
    
    response = (
        f"📈 <b>ATH Analysis for {token_info.get('name', 'Unknown Token')} ({token_info.get('symbol', 'N/A')})</b>\n\n"
        f"Contract: `{token_address}`\n\n"
        f"• Current Market Cap: ${format_number(ath_data.get('cur_mcap', 'N/A'))}\n"
        f"• ATH Market Cap: ${format_number(ath_data.get('ath_mcap', 'N/A'))}\n"
        f"• ATH Date: {ath_data.get('ath_date', 'N/A')}\n"
        f"• Current % of ATH: {percent_from_ath}%\n\n"
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
            f"   ATH Market Cap: ${format_number(token.get('ath_mcap', 'N/A'))}\n"
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


#wallet analysis input
async def handle_wallet_analysis_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    analysis_type: str,
    get_data_func,
    format_response_func,
    scan_count_type: str,
    processing_message_text: str,
    error_message_text: str,
    no_data_message_text: str,
) -> None:
    """
    Generic handler for wallet analysis inputs
    
    Args:
        update: The update object
        context: The context object
        analysis_type: Type of analysis being performed (for logging)
        get_data_func: Function to get the data (takes wallet_address)
        format_response_func: Function to format the response (takes data)
        scan_count_type: Type of scan to increment count for
        processing_message_text: Text to show while processing
        error_message_text: Text to show on error
        no_data_message_text: Text to show when no data is found
        additional_params: Additional parameters to pass to get_data_func
    """
    wallet_address = update.message.text.strip()
    selected_chain = context.user_data.get("selected_chain", "eth")
    
    if not await is_valid_wallet_address(wallet_address, selected_chain):
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
               
        await update.message.reply_text(
            f"⚠️ Something went wrong.⚠️ Please provide a valid wallet address on {selected_chain}.",
            reply_markup=reply_markup
        )
        return
    
    # Send processing message
    processing_message = await update.message.reply_text(processing_message_text)
    try:
        # Get data
        data = await get_data_func(wallet_address, selected_chain)
        
        if not data:
            # Add back button when no data is found
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_message.edit_text(
                no_data_message_text,
                reply_markup=reply_markup
            )
            return
        
        # Format the response
        response, keyboard = format_response_func(data, wallet_address)
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
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_message.edit_text(
            error_message_text,
            reply_markup=reply_markup
        )

def format_wallet_holding_duration_response(data: dict, wallet_address: str) -> tuple:
    """
    Format the response for wallet holding duration analysis
    
    Args:
        data: Wallet holding duration data
        wallet_address: The wallet address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    response = (
        f"⏳ <b>Wallet Holding Duration Analysis</b>\n\n"
        f"👛 <b>Wallet:</b> `{wallet_address[:6]}...{wallet_address[-4:]}`\n"
        f"🌐 <b>Chain:</b> {data.get('chain', 'ETH').upper()}\n\n"
        f"📊 <b>Average Holding Time:</b> {data.get('avg_holding_time_days', 'N/A')} days\n"
        f"🔎 <b>Tokens Analyzed:</b> {data.get('tokens_analyzed', 'N/A')}\n\n"
        f"📈 <b>Holding Duration Distribution:</b>\n"
        f"• ⏱️ Less than 1 day: {data['holding_distribution'].get('less_than_1_day', 'N/A')}%\n"
        f"• 📅 1 to 7 days: {data['holding_distribution'].get('1_to_7_days', 'N/A')}%\n"
        f"• 🗓️ 7 to 30 days: {data['holding_distribution'].get('7_to_30_days', 'N/A')}%\n"
        f"• 🏦 More than 30 days: {data['holding_distribution'].get('more_than_30_days', 'N/A')}%\n\n"
        f"🔬 <b>Tokens Held:</b>\n"
        f"These are the actual tokens this wallet has interacted with, providing a clear snapshot of its on-chain behavior. 🚀🔍\n\n"
    )

    
    # Add example tokens
    for i, token in enumerate(data.get('token_examples', [])[:5], 1):
        profit_str = f"+${token['profit']}" if token['profit'] > 0 else f"-${abs(token['profit'])}"
        response += (
            f"{i}. {token.get('name', 'Unknown')} ({token.get('symbol', 'N/A')})\n"
            f"   Held for: {token.get('holding_days', 'N/A')} days\n"
            f"   Profit: {profit_str}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
    
    return response, keyboard

def format_wallet_most_profitable_response(data: list, wallet_address: str = None) -> tuple:
    """
    Format the response for most profitable wallets analysis
    
    Args:
        data: List of profitable wallet data
        wallet_address: Not used for this function, but kept for consistency
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    # Get the first wallet to extract period info
    first_wallet = data[0] if data else {}
    period_days = first_wallet.get('period_days', 30)
    chain = first_wallet.get('chain', 'eth').upper()
    
    response = (
        f"💰 <b>Most Profitable Wallets Over the Last {period_days} Days</b>\n"
        f"🌐 Chain Analyzed: <b>{chain}</b>\n\n"
        f"📈 Below is a list of the most profitable wallets based on their transaction activity and earnings during this period. "
        f"These wallets have shown strong performance and smart trading behavior that contributed to significant gains. "
        f"Dive into the details to see who's leading the profit charts! 🚀💼\n\n"
    )
    
    for i, wallet in enumerate(data[:10], 1):
        response += (
            f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Profit: ${wallet.get('total_profit', 'N/A'):,.2f}\n"
            f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
            f"   Trades: {wallet.get('trades_count', 'N/A')}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
    
    return response, keyboard

def format_deployer_wallets_response(data: list, wallet_address: str = None) -> tuple:
    """
    Format the response for most profitable token deployer wallets
    
    Args:
        data: List of profitable deployer wallet data
        wallet_address: Not used for this function, but kept for consistency
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    # Get the first wallet to extract period info
    first_wallet = data[0] if data else {}
    period_days = first_wallet.get('period_days', 30)
    chain = first_wallet.get('chain', 'eth').upper()
    
    response = (
        f"🧪 <b>Most Profitable Token Deployer Wallets (Last {period_days} Days)</b>\n"
        f"🔗 Chain: <b>{chain}</b>\n\n"
        f"🚀 These wallet addresses have been busy deploying tokens and cashing in big over the last {period_days} days. "
        f"They’re not just developers — they’re trendsetters, launching tokens that gain traction fast! 💸📊\n\n"
        f"🔥 Let’s take a closer look at the top-performing deployers who are making serious moves in the ecosystem.\n\n"
    ) 
    
    for i, wallet in enumerate(data[:10], 1):
        response += (
            f"{i}. `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Tokens Deployed: {wallet.get('tokens_deployed', 'N/A')}\n"
            f"   Success Rate: {wallet.get('success_rate', 'N/A')}%\n"
            f"   Profit: ${wallet.get('total_profit', 'N/A'):,.2f}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
    
    return response, keyboard

def format_tokens_deployed_response(data: list, wallet_address: str) -> tuple:
    """
    Format the response for tokens deployed by wallet
    
    Args:
        data: List of token data
        wallet_address: The wallet address
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    chain = data[0].get('chain', 'eth').upper() if data else 'ETH'
    
    response = (
        f"🚀 <b>Tokens Deployed by Wallet</b>\n\n"
        f"👤 <b>Deployer:</b> `{wallet_address[:6]}...{wallet_address[-4:]}`\n"
        f"🌐 <b>Chain:</b> {chain}\n"
        f"🧬 <b>Total Tokens Deployed:</b> {len(data)}\n\n"
        f"🔍 This wallet has been actively creating tokens on {chain}, possibly experimenting, launching new projects, or fueling DeFi/NFT ecosystems. "
        f"Whether it’s for innovation or hype, it’s clearly making moves! 💼📈\n\n"
    )
    
    for i, token in enumerate(data[:5], 1):
        response += (
            f"{i}. {token.get('name', 'Unknown')} ({token.get('symbol', 'N/A')})\n"
            f"   Deployed: {token.get('deploy_date', 'N/A')}\n"
            f"   Current Price: ${token.get('current_price', 'N/A')}\n"
            f"   Market Cap: ${token.get('current_market_cap', 'N/A'):,.2f}\n"
            f"   ATH Multiple: {token.get('ath_multiplier', 'N/A')}x\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]]
    
    return response, keyboard

# Add these chain selection functions for wallet analysis

async def prompt_wallet_chain_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str) -> None:
    """
    Generic function to prompt user to select a blockchain network for wallet analysis
    
    Args:
        update: The update object
        context: The context object
        feature: The feature identifier (e.g., 'wallet_holding_duration', etc.)
    """
    query = update.callback_query
    
    # Create feature-specific callback data
    callback_prefix = f"{feature}_chain_"
    
    # Create keyboard with chain options
    keyboard = [
        [
            InlineKeyboardButton("Ethereum", callback_data=f"{callback_prefix}eth"),
            InlineKeyboardButton("Base", callback_data=f"{callback_prefix}base"),
            InlineKeyboardButton("BSC", callback_data=f"{callback_prefix}bsc")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Store the feature in context for later use
    context.user_data["current_feature"] = feature

    # Show chain selection message
    await query.edit_message_text(
        "🔗 <b>Select Blockchain Network</b>\n\n"
        "Please choose the blockchain network for wallet analysis:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# async def handle_wallet_chain_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Handle wallet chain selection callbacks"""
#     query = update.callback_query
#     callback_data = query.data
    
#     # Extract feature and chain from callback data
#     # Format: "{feature}_chain_{chain}"
#     parts = callback_data.split("_chain_")
#     if len(parts) != 2:
#         await query.answer("Invalid selection", show_alert=True)
#         return
    
#     feature = parts[0]
#     chain = parts[1]
    
#     # Store the selected chain in user_data
#     context.user_data["selected_chain"] = chain
    
#     # Map of feature to expecting state and display name
#     feature_map = {
#         "wallet_holding_duration": {
#             "expecting": "wallet_holding_duration_address",
#             "display": "holding duration"
#         },
#         "wallet_most_profitable_in_period": {
#             "expecting": "wallet_most_profitable_params",
#             "display": "most profitable wallets"
#         },
#         "most_profitable_token_deployer_wallet": {
#             "expecting": "most_profitable_token_deployer_params",
#             "display": "most profitable token deployers"
#         },
#         "tokens_deployed_by_wallet": {
#             "expecting": "tokens_deployed_wallet_address",
#             "display": "tokens deployed"
#         }
#     }
    
#     # Get feature info
#     feature_info = feature_map.get(feature, {"expecting": "unknown", "display": feature})
    
#     # Get chain display name
#     from services.blockchain import get_chain_display_name
#     chain_display = get_chain_display_name(chain)
    
#     # Handle features that need parameters vs. those that need wallet addresses
#     if feature == "wallet_most_profitable_in_period":
#         # For features that need parameters
#         keyboard = [
#             [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             f"🔍 <b>Wallet Analysis on {chain_display}</b>\n\n"
#             f"Please enter parameters for {feature_info['display']} in this format:\n\n"
#             f"`<days> <min_trades> <min_profit_usd>`\n\n"
#             f"Example: `30 10 1000`\n\n"
#             f"This will find wallets active in the last 30 days, with at least 10 trades, "
#             f"and minimum profit of $1,000.",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#     elif feature == "most_profitable_token_deployer_wallet":
#         # For features that need parameters
#         keyboard = [
#             [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             f"🔍 <b>Wallet Analysis on {chain_display}</b>\n\n"
#             f"Please enter parameters for {feature_info['display']} in this format:\n\n"
#             f"`<days> <min_tokens> <min_success_rate>`\n\n"
#             f"Example: `30 5 50`\n\n"
#             f"This will find deployers active in the last 30 days, with at least 5 tokens deployed, "
#             f"and minimum success rate of 50%.",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
#     else:
#         # For features that need wallet addresses
#         keyboard = [
#             [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             f"🔍 <b>Wallet Analysis on {chain_display}</b>\n\n"
#             f"Please send me the wallet address to analyze its {feature_info['display']}.\n\n"
#             f"Example: `0x1234...abcd`",
#             reply_markup=reply_markup,
#             parse_mode=ParseMode.HTML
#         )
    
#     # Set conversation state to expect input for the specific feature
#     context.user_data["expecting"] = feature_info["expecting"]


# kol wallet profitability
def format_kol_wallet_profitability_response(data: list) -> tuple:
    """
    Format KOL wallet profitability response
    
    Args:
        data: List of KOL wallet profitability data
        
    Returns:
        Tuple of (formatted response text, keyboard buttons)
    """
    period = data[0].get("period", 30) if data else 30
    
    response = (
        f"👑 <b>KOL Wallets Profitability Analysis - {period} Day Overview</b>\n\n"
        f"🧬 <b>Total KOL Wallets Analyzed:</b> A total of {len(data)} influential KOL (Key Opinion Leader) wallets were included in this report, offering a unique glimpse into how the most impactful traders and investors have been performing during the selected period.\n\n"
    )

    for i, wallet in enumerate(data, 1):
        response += (
            f"{i}. <b>{wallet.get('name', 'Unknown KOL')}</b>\n"
            f"   Wallet: `{wallet['address'][:6]}...{wallet['address'][-4:]}`\n"
            f"   Win Rate: {wallet.get('win_rate', 'N/A')}%\n"
            f"   {period}-Day Profit: ${wallet.get('period_profit', 'N/A'):,.2f}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="kol_wallets")]]
    
    return response, keyboard


async def handle_wallet_holding_duration_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle wallet holding duration input"""
    from utils import handle_wallet_analysis_input
    from data.database import get_wallet_holding_duration
    
    await handle_wallet_analysis_input(
        update=update,
        context=context,
        analysis_type="wallet_holding_duration",
        get_data_func=get_wallet_holding_duration,
        format_response_func=format_wallet_holding_duration_response,
        scan_count_type="wallet_scan",
        processing_message_text="🔍 Analyzing wallet holding duration... This may take a moment.",
        error_message_text="❌ An error occurred while analyzing the wallet. Please try again later.",
        no_data_message_text="❌ Could not find holding duration data for this wallet."
    )

async def handle_tokens_deployed_wallet_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tokens deployed by wallet input"""
    from utils import handle_wallet_analysis_input
    from data.database import get_tokens_deployed_by_wallet
    
    await handle_wallet_analysis_input(
        update=update,
        context=context,
        analysis_type="tokens_deployed_by_wallet",
        get_data_func=get_tokens_deployed_by_wallet,
        format_response_func=format_tokens_deployed_response,
        scan_count_type="wallet_scan",
        processing_message_text="🔍 Finding tokens deployed by this wallet... This may take a moment.",
        error_message_text="❌ An error occurred while analyzing the wallet. Please try again later.",
        no_data_message_text="❌ Could not find any tokens deployed by this wallet."
    )

async def handle_period_selection(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    feature_info:str, 
    scan_type: str,
    callback_prefix: str
) -> None:
    """
    Generic handler for period selection
    
    Args:
        update: The update object
        context: The context object

        scan_type: Name of the feature for rate limiting
        title: Title to display in the message
        callback_prefix: Prefix for callback data
    """
    query = update.callback_query
    user = await check_callback_user(update)
    
    # Check if user has reached daily limit
    has_reached_limit, current_count = await check_rate_limit_service(
        user.user_id, scan_type, FREE_WALLET_SCANS_DAILY
    )
    
    if has_reached_limit and not user.is_premium:
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium_info")],
            [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"You’ve already used <b>{current_count}</b> out of your <b>{FREE_WALLET_SCANS_DAILY}</b> free daily wallet scans available for today. 🚫\n\n"
            f"To unlock unlimited access to powerful wallet analysis features, upgrade to <b>Premium</b> and explore the full potential of on-chain intelligence. 💎\n"
            f"With Premium, you can scan as many wallets as you like, track top-performing traders, monitor token deployers, and much more — all without limits! 🚀",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # If user has not reached limit or is premium, show time period options
    keyboard = [
        [
            InlineKeyboardButton("1 Day", callback_data=f"{callback_prefix}_1"),
            InlineKeyboardButton("7 Days", callback_data=f"{callback_prefix}_7"),
            InlineKeyboardButton("30 Days", callback_data=f"{callback_prefix}_30")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="wallet_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get the selected chain
    selected_chain = context.user_data.get("selected_chain", "eth")
    
    await query.message.reply_text(
        f"🔍 <b>Analyzing {feature_info} on {selected_chain}</b>\n\n"
        f"To proceed with a more in-depth analysis, please choose the time period you'd like to examine. "
        f"This will help us provide insights that are both accurate and relevant to your needs.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


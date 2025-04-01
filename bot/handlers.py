from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from services.blockchain_service import BlockchainService
from services.token_service import TokenService
from services.wallet_service import WalletService
from services.deployer_service import DeployerService
from services.tracking_service import TrackingService
from models.user import User
from database.user_repository import UserRepository
from config import COMMAND_DESCRIPTIONS, FREE_PROFITABLE_WALLETS_LIMIT

# Initialize services
blockchain_service = BlockchainService()
token_service = TokenService()
wallet_service = WalletService()
deployer_service = DeployerService()
tracking_service = TrackingService()
user_repository = UserRepository()

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Create or get user
    user = await user_repository.get_or_create_user(user_id, username)
    
    welcome_message = (
        f"👋 Welcome to DeFi Scope Bot, {update.effective_user.first_name}!\n\n"
        f"This bot helps you analyze DeFi tokens, wallets, and market data.\n\n"
        f"🔹 Free users: Limited to 3 token scans and 3 wallet scans daily\n"
        f"🔸 Premium users: Unlimited scans and exclusive features\n\n"
        f"Type /help to see all available commands."
    )
    
    # Create premium button
    keyboard = [
        [InlineKeyboardButton("Upgrade to Premium 💎", callback_data="premium_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    help_text = "📚 **Available Commands:**\n\n"
    
    # Free commands
    help_text += "**Free Commands:**\n"
    help_text += "/fb [number 1-50] [token_address] - First buy wallets of a token\n"
    help_text += "/mpw [token_address] - Most profitable wallets in a token\n"
    help_text += "/mpw [days 1-30] - Most profitable wallets in time period\n"
    help_text += "/wh [wallet_address] - Wallet holding time for tokens\n"
    help_text += "/ptd [days 1-30] - Profitable token deployer wallets\n"
    help_text += "/kol [name] [days 1-30] - KOL wallets profitability\n"
    help_text += "/ath [token_address] - All time high market cap\n\n"
    
    # Premium commands
    help_text += "**Premium Commands:**\n"
    help_text += "/td [wallet_address] - Tokens deployed by a wallet\n"
    help_text += "/dw [token_address] - Deployer wallet analysis\n"
    help_text += "/th [token_address] - Top holders analysis\n"
    help_text += "/track [token_address] - Track token for notifications\n"
    help_text += "/track wd [wallet_address] - Track wallet deployments\n"
    help_text += "/track wbs [wallet_address] - Track wallet buys/sells\n"
    help_text += "/pw [max_trades] [max_buy] [days] [token] - Profitable wallets\n"
    help_text += "/hnw [token_address] - High net worth holders\n\n"
    
    # Utility commands
    help_text += "**Utility Commands:**\n"
    help_text += "/premium - Upgrade to premium\n"
    help_text += "/usage - Check your usage statistics\n"
    
    # Create premium button
    keyboard = [
        [InlineKeyboardButton("Upgrade to Premium 💎", callback_data="premium_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")

async def fb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """First 1-50 buy wallets of a token with analytics"""
    user_id = update.effective_user.id
    user = await user_repository.get_user(user_id)
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Incorrect format. Use: /fb [number 1-50] [token_address]"
        )
        return
    
    try:
        num_wallets = int(context.args[0])
        token_address = context.args[1]
        
        if not 1 <= num_wallets <= 50:
            await update.message.reply_text("❌ Number of wallets must be between 1 and 50.")
            return
            
        # Check if token address is valid
        if not blockchain_service.is_valid_address(token_address):
            await update.message.reply_text("❌ Invalid token address.")
            return
            
        await update.message.reply_text(f"🔍 Analyzing first {num_wallets} buy wallets for token {token_address}...\nThis may take a moment.")
        
        # Get first buy wallets data
        wallets_data = await token_service.get_first_buy_wallets(token_address, num_wallets)
        
        if not wallets_data:
            await update.message.reply_text("❌ Could not retrieve wallet data for this token.")
            return
            
        # Format response
        response = f"📊 First {len(wallets_data)} Buy Wallets for {wallets_data['token_name']} ({wallets_data['token_symbol']})\n\n"
        
        for idx, wallet in enumerate(wallets_data['wallets'], 1):
            response += (
                f"{idx}. `{wallet['address']}`\n"
                f"   Buy: ${wallet['buy_amount']:.2f} ({wallet['buy_trades']} trades)\n"
                f"   Sell: ${wallet['sell_amount']:.2f} ({wallet['sell_trades']} trades)\n"
                f"   Total Trades: {wallet['total_trades']}\n"
                f"   PNL: ${wallet['pnl']:.2f} ({wallet['win_rate']}% win rate)\n\n"
            )
            
        # Update user's usage count
        if not user.is_premium:
            await user_repository.increment_token_scan_count(user_id)
            scans_left = user_repository.FREE_TOKEN_SCANS_DAILY - user.token_scans_today
            response += f"\n⚠️ You have {scans_left} free token scans left today. Upgrade to premium for unlimited scans!"
            
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in fb_command: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

# Implementing one more command as an example
async def mpw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Most profitable wallets in a token or time period"""
    user_id = update.effective_user.id
    user = await user_repository.get_user(user_id)
    
    if not context.args or len(context.args) > 1:
        await update.message.reply_text(
            "❌ Incorrect format. Use either:\n"
            "/mpw [token_address] - For token analysis\n"
            "/mpw [days 1-30] - For time period analysis"
        )
        return
    
    arg = context.args[0]
    
    try:
        # Check if the argument is a number (days) or an address
        if arg.isdigit():

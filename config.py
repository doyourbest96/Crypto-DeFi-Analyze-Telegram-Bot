import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Blockchain API keys
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
INFURA_ENDPOINT = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

# Database
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "defi_scope_bot"

# Rate limits for free users
FREE_TOKEN_SCANS_DAILY = 3
FREE_WALLET_SCANS_DAILY = 3
FREE_PROFITABLE_WALLETS_LIMIT = 2

# Command descriptions
COMMAND_DESCRIPTIONS = {
    "start": "Start the bot and get information",
    "help": "Show available commands and their usage",
    "fb": "First 1-50 buy wallets of a token with analytics",
    "mpw": "Most profitable wallets in a token or time period",
    "wh": "How long a wallet holds a token before selling",
    "ptd": "Most profitable token deployer wallets",
    "kol": "KOL wallets profitability",
    "td": "Tokens deployed by a particular wallet (Premium)",
    "ath": "All time high market cap of any token",
    "dw": "Scan a token contract to reveal the deployer wallet (Premium)",
    "th": "Scan a token contract to see top 10 holders (Premium)",
    "track": "Track tokens or wallets for notifications (Premium)",
    "pw": "Profitable wallets in any token with detailed metrics (Premium)",
    "hnw": "High net worth wallet holders of any token (Premium)",
    "premium": "Upgrade to premium membership",
    "usage": "Check your usage statistics"
}

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_IDS = list(map(int, os.getenv("ADMIN_USER_IDS", "").split(",")))

# Blockchain configuration
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

# Database configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "defi_scope_bot")

# Rate limits for free users
FREE_TOKEN_SCANS_DAILY = 3
FREE_WALLET_SCANS_DAILY = 3
FREE_PROFITABLE_WALLETS_LIMIT = 2

# Command descriptions for bot menu
COMMAND_DESCRIPTIONS = {
    "fb": "First 1-50 buy wallets of a token",
    "mpw": "Most profitable wallets in a token or time period",
    "wh": "How long a wallet holds a token before selling",
    "ptd": "Most profitable token deployer wallets",
    "kol": "KOL wallets profitability",
    "td": "Tokens deployed by a wallet (Premium)",
    "ath": "All time high market cap of a token",
    "dw": "Scan token contract to reveal deployer wallet (Premium)",
    "th": "Scan token for top holders (Premium)",
    "track": "Track tokens, wallets or deployments (Premium)",
    "pw": "Profitable wallets in any token (Premium)",
    "hnw": "High net worth wallet holders (Premium)",
    "premium": "Upgrade to premium",
    "help": "Show help information",
}

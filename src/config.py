import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Bot configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_IDS = list(map(int, os.getenv("ADMIN_USER_IDS", "").split(",")))

# Blockchain configuration
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")
CHAINLINK_ETH_USD_PRICE_FEED_ADDRESS = os.getenv("CHAINLINK_ETH_USD_PRICE_FEED_ADDRESS")
SUBSCRIPTION_WALLET_ADDRESS=os.getenv("SUBSCRIPTION_WALLET_ADDRESS")

# Database configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "defi_scope_bot")

# Rate limits for free users
FREE_FIRST_BUYER_SCANS_DAILY=3
FREE_TOKEN_MOST_PROFITABLE_WALLETS_DAILY=3
FREE_ATH_SCANS_DAILY = 3

FREE_WALLET_MOST_PROFITABLE_TOKENS_IN_PERIOD_DAILY = 3

FREE_TOKEN_SCANS_DAILY = 3
FREE_WALLET_SCANS_DAILY = 3
FREE_PROFITABLE_WALLETS_LIMIT = 2

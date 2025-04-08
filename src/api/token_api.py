import logging
from api.client import api_client
from config import API_BASE_URL

logger = logging.getLogger(__name__)

async def fetch_token_metadata(chain, token_address):
    """Fetch basic token metadata"""
    url = f"{API_BASE_URL}/api/v1/token_meta/{chain}/{token_address}"
    logger.info(f"Fetching token metadata for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_market_cap(chain, token_address):
    """Fetch token market cap data"""
    url = f"{API_BASE_URL}/api/v1/ath_mcap/{chain}/{token_address}"
    logger.info(f"Fetching market cap for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_token_holders(chain, token_address, limit=10):
    """Fetch top token holders"""
    url = f"{API_BASE_URL}/api/v1/top_holders/{chain}/{token_address}/{limit}"
    logger.info(f"Fetching top {limit} holders for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_token_security(chain, token_address):
    """Fetch token security information"""
    url = f"{API_BASE_URL}/api/v1/token_security/{chain}/{token_address}"
    logger.info(f"Fetching security info for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_first_buyers(chain, token_address):
    """Fetch token deployer and first buyers"""
    url = f"{API_BASE_URL}/api/v1/first_buyers/{chain}/{token_address}"
    logger.info(f"Fetching first buyers for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_token_profitable_wallets(chain, token_address):
    """Fetch most profitable wallets for a given token"""
    url = f"{API_BASE_URL}/api/v1/token_profitable_wallets/{chain}/{token_address}"
    logger.info(f"Fetching profitable wallets for {chain}:{token_address}")
    return await api_client.get(url)

async def fetch_token_deployer_projects(chain, token_address):
    """Fetch other tokens deployed by the same deployer"""
    url = f"{API_BASE_URL}/api/v1/token_deployer_projects/{chain}/{token_address}"
    logger.info(f"Fetching deployer projects for {chain}:{token_address}")
    return await api_client.get(url)

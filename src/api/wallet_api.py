import logging
from api.client import api_client
from config import API_BASE_URL

logger = logging.getLogger(__name__)

async def fetch_wallet_stats(chain, wallet_address, period="all"):
    """Fetch wallet trading statistics"""
    url = f"{API_BASE_URL}/api/v1/wallet_stat/{chain}/{wallet_address}/{period}"
    logger.info(f"Fetching wallet stats for {chain}:{wallet_address} period:{period}")
    return await api_client.get(url)

async def fetch_kol_wallets(chain, order_by="pnl_1d"):
    """Fetch kol_wallets on a specific blockchain"""
    url = f"{API_BASE_URL}/api/v1/kol_wallets/{chain}/{order_by}"
    logger.info(f"Fetching kol_wallets for {chain}, order_by: {order_by}")
    return await api_client.get(url)

async def fetch_wallet_holding_time(chain, wallet_address):
    """Fetch wallet token holding time analysis"""
    url = f"{API_BASE_URL}/api/v1/wallet_holding_time/{chain}/{wallet_address}"
    logger.info(f"Fetching wallet holding time for {chain}:{wallet_address}")
    return await api_client.get(url)

async def fetch_wallet_deployed_tokens(chain, wallet_address):
    """Fetch tokens deployed by a wallet"""
    url = f"{API_BASE_URL}/api/v1/wallet_deployed_tokens/{chain}/{wallet_address}"
    logger.info(f"Fetching deployed tokens for {chain}:{wallet_address}")
    return await api_client.get(url)

async def fetch_high_activity_wallets(chain):
    """Fetch high activity wallets by volume for a chain"""
    url = f"{API_BASE_URL}/api/v1/high_activity_wallets/{chain}"
    logger.info(f"Fetching high activity wallets for {chain}")
    return await api_client.get(url)

async def fetch_high_transaction_wallets(chain):
    """Fetch high activity wallets by transaction count for a chain"""
    url = f"{API_BASE_URL}/api/v1/high_transaction_wallets/{chain}"
    logger.info(f"Fetching high transaction wallets for {chain}")
    return await api_client.get(url)

async def fetch_profitable_deployers(chain):
    """Fetch most profitable token deployer wallets for a chain"""
    url = f"{API_BASE_URL}/api/v1/profitable_deployers/{chain}"
    logger.info(f"Fetching profitable deployers for {chain}")
    return await api_client.get(url)

async def fetch_profitable_defi_wallets(chain):
    """Fetch most profitable DeFi trading wallets for a chain"""
    url = f"{API_BASE_URL}/api/v1/profitable_defi_wallets/{chain}"
    logger.info(f"Fetching profitable DeFi wallets for {chain}")
    return await api_client.get(url)

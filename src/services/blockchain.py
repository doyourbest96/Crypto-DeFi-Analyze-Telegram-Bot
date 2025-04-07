import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import re
from web3 import Web3
from web3.exceptions import InvalidAddress, ContractLogicError

from config import WEB3_PROVIDER_URI
# Configure web3 connection
# This would be replaced with your actual blockchain node connection
w3_eth = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{WEB3_PROVIDER_URI}"))
w3_base = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
w3_bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

async def is_valid_address(address: str) -> bool:
    if not address:
        return False
    
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return False
    
    return True

async def is_valid_token_contract(address: str, chain:str) -> bool:
    """
    Validate if the provided address is a valid token contract
    
    Args:
        address: The contract address to validate
        chain: The blockchain network (eth, base, bsc)
    
    Returns:
        bool: True if the address is a valid token contract, False otherwise
    """
    # First check if it's a valid address
    if not await is_valid_address(address):
        return False
    
    # Get the appropriate web3 provider
    w3 = get_web3_provider(chain)
    
    try:
        try:
            checksum_address = w3.to_checksum_address(address.lower())
        except ValueError as e:
            logging.error(f"Invalid address format: {e}")
            return False
            
        code = w3.eth.get_code(checksum_address)
        print(f"Code at address {address}: {code}")

        if code == b'' or code == '0x':
            return False  # No code at this address, not a contract
        
        # Try to instantiate the contract with ERC20 ABI
        contract = w3.eth.contract(address=address, abi=ERC20_ABI)
        
        # Try to call some standard ERC20 functions
        try:
            symbol = contract.functions.symbol().call()
            logging.info(f"Token symbol: {symbol}")
            return True
        except Exception as e:
            logging.warning(f"Error getting token symbol: {e}")
        
        try:
            name = contract.functions.name().call()
            logging.info(f"Token name: {name}")
            return True
        except Exception as e:
            logging.warning(f"Error getting token name: {e}")
        
        try:
            decimals = contract.functions.decimals().call()
            logging.info(f"Token decimals: {decimals}")
            return True
        except Exception as e:
            logging.warning(f"Error getting token decimals: {e}")
        
        # If we couldn't successfully call any ERC20 functions, it might not be a token
        logging.warning(f"Address {address} has code but doesn't appear to be an ERC20 token")
        return False
        
    except Exception as e:
        logging.error(f"Error validating token contract on {chain}: {e}")
        # Return False if we encounter any errors
        return False

async def is_valid_wallet_address(address: str, chain:str) -> bool:
    """
    Validate if the provided address is a wallet (not a contract)
    
    Args:
        address: The address to validate
        chain: The blockchain network (eth, base, bsc)
    
    Returns:
        bool: True if the address is a valid wallet, False otherwise
    """
    # First check if it's a valid address
    if not await is_valid_address(address):
        return False
    
    w3 = get_web3_provider(chain)
    
    try:
        checksum_address = w3.to_checksum_address(address)
        code = w3.eth.get_code(checksum_address)
        # If there's no code, it's a regular wallet address
        return code == b'' or code == '0x'
    except Exception as e:
        logging.error(f"Error validating wallet address on {chain}: {e}")
        # Return True if the format is correct but web3 validation fails
        # This is a fallback to prevent false negatives due to connection issues
        return True

def get_web3_provider(chain: str):
    """
    Get the appropriate Web3 provider for the specified chain
    
    Args:
        chain: The blockchain network (eth, base, bsc)
    
    Returns:
        Web3: The Web3 provider for the specified chain
    """
    if chain == "eth":
        return w3_eth
    elif chain == "base":
        return w3_base
    elif chain == "bsc":
        return w3_bsc
    else:
        logging.warning(f"Unknown chain '{chain}', defaulting to Ethereum")
        return w3_eth

def check_providers():
    """Check if all blockchain providers are connected"""
    eth_connected = w3_eth.is_connected()
    base_connected = w3_base.is_connected()
    bsc_connected = w3_bsc.is_connected()
    
    if not (eth_connected and base_connected and bsc_connected):
        logging.warning(f"Provider connection status: ETH: {eth_connected}, BASE: {base_connected}, BSC: {bsc_connected}")
    
    return eth_connected, base_connected, bsc_connected

# def get_chain_display_name(chain: str) -> str:
#     """Get a user-friendly display name for a chain"""
#     chain_display = {
#         "eth": "🌐 Ethereum",
#         "base": "🛡️ Base",
#         "bsc": "🔶 BSC"
#     }
#     return chain_display.get(chain, chain.upper())

# async def get_wallet_info(wallet_address: str, chain: str = "eth") -> Optional[Dict[str, Any]]:
#     """Get detailed information about a wallet"""
#     if not await is_valid_wallet_address(wallet_address, chain):
#         return None
    
#     try:
#         # This would be replaced with actual blockchain query
#         # For now, we'll simulate the data
        
#         # Get the appropriate web3 provider based on chain
#         w3 = get_web3_provider(chain)
        
#         # Get wallet balance
#         balance = w3.eth.get_balance(wallet_address)
#         balance_eth = w3.from_wei(balance, 'ether')
        
#         # Simulate token holdings and other data
#         return {
#             "address": wallet_address,
#             "balance_eth": balance_eth,
#             "first_transaction": "2021-05-12",
#             "last_transaction": "2023-09-28",
#             "total_transactions": 156,
#             "chain": chain,  # Include the chain in the response
#             "token_holdings": [
#                 {"token_address": f"0x{i}token{wallet_address[-4:]}", "symbol": f"TKN{i}", "amount": i * 1000, "value_usd": i * 1000 * 0.5}
#                 for i in range(1, 6)
#             ],
#             "deployed_tokens": [
#                 {"address": f"0x{i}deployed{wallet_address[-4:]}", "name": f"Token {i}", "symbol": f"TKN{i}", "deploy_date": f"2022-{i}-15", "success_rate": 70 + i * 5}
#                 for i in range(1, 4)
#             ],
#             "win_rate": 68,
#             "total_profit": 15600
#         }
#     except Exception as e:
#         logging.error(f"Error getting wallet info on {chain}: {e}")
#         return None

# async def get_first_buyers(token_address: str, chain:str ='eth') -> List[Dict[str, Any]]:
#     """Get the first buyers of a token"""
#     if not await is_valid_token_contract(token_address, chain):
#         return []
    
#     try:
#         # This would be replaced with actual blockchain query
#         # For now, we'll simulate the data
#         return [
#             {"address": f"0x{i}buyer{token_address[-4:]}", "amount": i * 1000, "time": f"2023-09-{10+i} 14:{i*5}:00"}
#             for i in range(1, 51)
#         ]
#     except Exception as e:
#         logging.error(f"Error getting first buyers: {e}")
#         return []

# async def get_token_holders(token_address: str, chain:str ='eth') -> List[Dict[str, Any]]:
#     """Get the top holders of a token"""
#     if not await is_valid_token_contract(token_address, chain):
#         return []
    
#     try:
#         # This would be replaced with actual blockchain query
#         # For now, we'll simulate the data
#         token_info = await get_token_info(token_address)
#         if not token_info:
#             return []
        
#         total_supply = token_info.get("total_supply", 1000000)
        
#         holders = []
#         remaining_percentage = 100
        
#         # Generate top holders with decreasing percentages
#         for i in range(1, 21):
#             if i <= 3:
#                 percentage = round(remaining_percentage * (0.2 - (i-1)*0.05), 2)
#             elif i <= 10:
#                 percentage = round(remaining_percentage * (0.05 - (i-4)*0.005), 2)
#             else:
#                 percentage = round(remaining_percentage * 0.01, 2)
            
#             remaining_percentage -= percentage
#             amount = total_supply * (percentage / 100)
#             value = amount * token_info.get("current_price", 0.001)
            
#             holders.append({
#                 "address": f"0x{i}holder{token_address[-4:]}",
#                 "amount": amount,
#                 "percentage": percentage,
#                 "value": round(value, 2)
#             })
        
#         return holders
#     except Exception as e:
#         logging.error(f"Error getting token holders: {e}")
#         return []


# async def get_wallet_holding_time(wallet_address: str, token_address: str) -> Optional[Dict[str, Any]]:
#     """Get information about how long a wallet holds a specific token"""
#     if not await is_valid_address(wallet_address) or not await is_valid_address(token_address):
#         return None
    
#     try:
#         # This would be replaced with actual blockchain query
#         # For now, we'll simulate the data
#         return {
#             "wallet_address": wallet_address,
#             "token_address": token_address,
#             "avg_holding_time": "3.5 days",
#             "longest_hold": "12 days",
#             "shortest_hold": "4 hours",
#             "total_trades": 8,
#             "buy_sell_ratio": "1.5:1"
#         }
#     except Exception as e:
#         logging.error(f"Error getting wallet holding time: {e}")
#         return None

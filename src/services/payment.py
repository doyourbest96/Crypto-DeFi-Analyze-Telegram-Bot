import logging
import aiohttp
from web3 import Web3
from typing import Dict, Any
from config import ETHERSCAN_API_KEY, WEB3_PROVIDER_URI, CHAINLINK_ETH_USD_PRICE_FEED_ADDRESS
from data.database import get_plan_price

async def verify_crypto_payment(
    transaction_id: str, 
    expected_amount: float, 
    wallet_address: str
) -> Dict[str, Any]:
    """
    Verify a crypto payment using the Etherscan API
    
    Args:
        transaction_id: The transaction hash/ID
        expected_amount: The expected payment amount in ETH
        wallet_address: Your wallet address that should receive the payment
        
    Returns:
        Dict containing verification result and transaction details
    """
    try:
        # Normalize addresses and transaction ID
        wallet_address = wallet_address.lower()
        transaction_id = transaction_id.lower()
        
        # Check if API key is configured
        if not ETHERSCAN_API_KEY:
            logging.error("Etherscan API key not found in environment variables")
            return {"verified": False, "error": "API configuration error"}
        
        # Create API URL for Etherscan
        api_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={transaction_id}&apikey={ETHERSCAN_API_KEY}"
        
        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    return {
                        "verified": False, 
                        "error": f"API request failed with status {response.status}"
                    }
                
                data = await response.json()
                
                # Check for API errors
                if data.get("error"):
                    return {
                        "verified": False, 
                        "error": data["error"].get("message", "API error")
                    }
                
                # Get transaction details
                result = data.get("result", {})
                
                # Check if transaction exists
                if not result:
                    return {"verified": False, "error": "Transaction not found"}
                
                # Check if transaction is to the correct wallet
                to_address = result.get("to", "").lower()
                if to_address != wallet_address:
                    return {
                        "verified": False, 
                        "error": "Wrong recipient wallet",
                        "expected": wallet_address,
                        "received": to_address
                    }
                
                # Check transaction value (convert from Wei to ETH)
                value_wei = int(result.get("value", "0"), 16)
                value_eth = value_wei / 10**18
                
                # Allow small difference (1%) due to gas fees and price fluctuations
                tolerance = expected_amount * 0.01
                if abs(value_eth - expected_amount) > tolerance:
                    return {
                        "verified": False, 
                        "error": "Payment amount mismatch",
                        "expected": expected_amount,
                        "received": value_eth
                    }
                
                # Check if transaction is confirmed (blockNumber exists)
                if not result.get("blockNumber"):
                    return {"verified": False, "error": "Transaction pending confirmation"}
                
                # Get receipt to check transaction status
                receipt_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionReceipt&txhash={transaction_id}&apikey={ETHERSCAN_API_KEY}"
                
                async with session.get(receipt_url) as receipt_response:
                    if receipt_response.status != 200:
                        return {"verified": False, "error": "Failed to get transaction receipt"}
                    
                    receipt_data = await receipt_response.json()
                    receipt = receipt_data.get("result", {})
                    
                    # Check transaction status (1 = success, 0 = failure)
                    status = int(receipt.get("status", "0x0"), 16)
                    if status != 1:
                        return {"verified": False, "error": "Transaction failed on blockchain"}
                
                # All checks passed
                block_number = int(result.get("blockNumber", "0"), 16)
                from_address = result.get("from", "").lower()
                
                # Get block timestamp to know when the transaction was confirmed
                block_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag=0x{block_number:x}&boolean=false&apikey={ETHERSCAN_API_KEY}"
                
                async with session.get(block_url) as block_response:
                    timestamp = None
                    if block_response.status == 200:
                        block_data = await block_response.json()
                        block = block_data.get("result", {})
                        timestamp_hex = block.get("timestamp", "0x0")
                        timestamp = int(timestamp_hex, 16)
                
                return {
                    "verified": True,
                    "transaction_id": transaction_id,
                    "amount": value_eth,
                    "block_number": block_number,
                    "from_address": from_address,
                    "timestamp": timestamp,
                    "confirmations": 1  # We know it's at least confirmed once
                }
    
    except Exception as e:
        logging.error(f"Error verifying crypto payment: {e}")
        return {"verified": False, "error": str(e)}

def get_eth_price_for_plan(plan: str) -> float:
    """
    Calculate the ETH amount required for a plan based on current ETH price
    
    Args:
        plan: The premium plan (monthly, quarterly, annual)
        eth_price_usd: Current ETH price in USD (default: $3000)
        
    Returns:
        The amount of ETH required for the plan
    """
    usd_price = get_plan_price(plan)
    eth_price_usd = get_eth_price_chainlink()
    eth_amount = usd_price / eth_price_usd
    
    # Round to 6 decimal places for readability
    return round(eth_amount, 6)

async def get_eth_price_chainlink() -> float:
    """Get ETH price from Chainlink price feed"""
    try:
        # Connect to an Ethereum node (use your own provider URL)
        w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{WEB3_PROVIDER_URI}'))
        
        abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"internalType": "uint80", "name": "roundId", "type": "uint80"},
                    {"internalType": "int256", "name": "answer", "type": "int256"},
                    {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
                    {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
                    {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        contract = w3.eth.contract(address=CHAINLINK_ETH_USD_PRICE_FEED_ADDRESS, abi=abi)
        
        round_data = contract.functions.latestRoundData().call()
        
        price = round_data[1] / 10**8
        
        return float(price)
    except Exception as e:
        logging.error(f"Error getting ETH price from Chainlink: {e}")
        return 2000.0  # Default fallback price

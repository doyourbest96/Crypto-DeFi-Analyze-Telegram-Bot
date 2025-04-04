import logging
import aiohttp
from web3 import Web3
from typing import Dict, Any, Tuple
from config import ETHERSCAN_API_KEY, WEB3_PROVIDER_URI, BSCSCAN_API_KEY, SUBSCRIPTION_WALLET_ADDRESS

async def verify_crypto_payment(
    transaction_id: str, 
    expected_amount: float, 
    wallet_address: str,
    network: str = "eth"  # Added network parameter to support ETH and BNB
) -> Dict[str, Any]:
    """
    Verify a crypto payment using the Etherscan/BSCScan API
    
    Args:
        transaction_id: The transaction hash/ID
        expected_amount: The expected payment amount in ETH/BNB
        wallet_address: Your wallet address that should receive the payment
        network: The blockchain network ("eth" or "bnb")
        
    Returns:
        Dict containing verification result and transaction details
    """
    try:
        # Normalize addresses and transaction ID
        wallet_address = wallet_address.lower()
        transaction_id = transaction_id.lower()
        
        # Select API key and base URL based on network
        if network.lower() == "bnb":
            api_key = BSCSCAN_API_KEY
            base_url = "https://api.bscscan.com/api"
            if not api_key:
                logging.error("BSCScan API key not found in environment variables")
                return {"verified": False, "error": "API configuration error"}
        else:
            api_key = ETHERSCAN_API_KEY
            base_url = "https://api.etherscan.io/api"
            if not api_key:
                logging.error("Etherscan API key not found in environment variables")
                return {"verified": False, "error": "API configuration error"}
        
        # Create API URL for transaction data
        api_url = f"{base_url}?module=proxy&action=eth_getTransactionByHash&txhash={transaction_id}&apikey={api_key}"
        
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
                
                # Check transaction value (convert from Wei to ETH/BNB)
                value_wei = int(result.get("value", "0"), 16)
                value_crypto = value_wei / 10**18
                
                # Allow small difference (1%) due to gas fees
                tolerance = expected_amount * 0.01
                if abs(value_crypto - expected_amount) > tolerance:
                    return {
                        "verified": False, 
                        "error": "Payment amount mismatch",
                        "expected": expected_amount,
                        "received": value_crypto
                    }
                
                # Check if transaction is confirmed (blockNumber exists)
                if not result.get("blockNumber"):
                    return {"verified": False, "error": "Transaction pending confirmation"}
                
                # Get receipt to check transaction status
                receipt_url = f"{base_url}?module=proxy&action=eth_getTransactionReceipt&txhash={transaction_id}&apikey={api_key}"
                
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
                block_url = f"{base_url}?module=proxy&action=eth_getBlockByNumber&tag=0x{block_number:x}&boolean=false&apikey={api_key}"
                
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
                    "amount": value_crypto,
                    "network": network,
                    "block_number": block_number,
                    "from_address": from_address,
                    "timestamp": timestamp,
                    "confirmations": 1  # We know it's at least confirmed once
                }
    
    except Exception as e:
        logging.error(f"Error verifying crypto payment: {e}")
        return {"verified": False, "error": str(e)}

def get_plan_payment_details(plan: str, currency: str = "eth") -> Dict[str, Any]:
    """Get complete payment details for a specific premium plan and currency"""
    plans = {
        "weekly": {
            "eth": {
                "amount": 0.1,
                "duration_days": 7,
                "display_name": "Weekly",
                "display_price": "0.1 ETH",
                "network": "eth"
            },
            "bnb": {
                "amount": 0.35,
                "duration_days": 7,
                "display_name": "Weekly",
                "display_price": "0.35 BNB",
                "network": "bnb"
            }
        },
        "monthly": {
            "eth": {
                "amount": 0.25,
                "duration_days": 30,
                "display_name": "Monthly",
                "display_price": "0.25 ETH",
                "network": "eth"
            },
            "bnb": {
                "amount": 1.0,
                "duration_days": 30,
                "display_name": "Monthly",
                "display_price": "1.0 BNB",
                "network": "bnb"
            }
        }
    }
    
    # Get the plan details or default to monthly ETH
    plan_details = plans.get(plan, {}).get(currency.lower(), plans["monthly"]["eth"]).copy()
    
    # Add wallet address and uppercase currency
    plan_details["wallet_address"] = SUBSCRIPTION_WALLET_ADDRESS
    plan_details["currency"] = currency.upper()
    
    return plan_details

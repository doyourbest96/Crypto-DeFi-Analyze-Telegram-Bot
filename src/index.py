import asyncio
import logging
import re
from web3 import Web3
# from web3.middleware import geth_poa_middleware

# 🚀 Sample ERC-20 ABI (just enough to validate token-ness)
ERC20_ABI = [
    {"constant": True, "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
]

# 🧠 Async address validation using Web3
async def is_valid_address(address: str) -> bool:
    if not address:
        return False
    return Web3.is_address(address)

# 🌐 Pick the right RPC provider based on chain name
def get_web3_provider(chain: str) -> Web3:
    rpc_urls = {
        "eth": "https://mainnet.infura.io/v3/29bb8bd1892e49eb8af5cea9060caa4e",
    }

    if chain not in rpc_urls:
        raise ValueError(f"Unsupported chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(rpc_urls[chain]))

    return w3

# 🔍 Check if a contract address is a valid ERC-20 token
async def is_valid_token_contract(address: str, chain: str) -> bool:
    if not await is_valid_address(address):
        logging.warning(f"Invalid address format: {address}")
        return False

    w3 = get_web3_provider(chain)

    try:
        checksum_address = w3.to_checksum_address(address.lower())
        code = w3.eth.get_code(checksum_address)

        if code == b'' or code == b'0x':
            logging.info("Address has no contract code.")
            return False

        contract = w3.eth.contract(address=checksum_address, abi=ERC20_ABI)

        try:
            symbol = contract.functions.symbol().call()
            logging.info(f"Token symbol: {symbol}")
        except Exception as e:
            logging.warning(f"Couldn't get token symbol: {e}")

        try:
            name = contract.functions.name().call()
            logging.info(f"Token name: {name}")
            return True
        except Exception as e:
            logging.warning(f"Couldn't get token name: {e}")

        try:
            decimals = contract.functions.decimals().call()
            logging.info(f"Token decimals: {decimals}")
            return True
        except Exception as e:
            logging.warning(f"Couldn't get token decimals: {e}")

        logging.warning("Address has code but no ERC-20 behavior.")
        return False

    except Exception as e:
        logging.error(f"Error validating token contract: {e}")
        return False

# 🚦 Entry point to test
async def main():
    test_addresses = [
        "0xa50ad00ce16fe2b0aabbb2db0ddf5590ff5769ff",  # GMGN (lowercase)
        "0xa50AD00ce16fE2B0AABbb2dB0ddf5590FF5769fF",  # Etherscan (checksummed)
        "0x0000000000000000000000000000000000000000",  # Invalid
    ]

    chain = "eth"  # Test on Ethereum mainnet

    for addr in test_addresses:
        result = await is_valid_token_contract(addr, chain)
        print(f"Address: {addr} → Valid ERC-20 Token? {result}")

# 🐍 Run the async main
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

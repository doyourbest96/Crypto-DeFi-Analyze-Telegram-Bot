import logging
import random
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection

from config import MONGODB_URI, DB_NAME, SUBSCRIPTION_WALLET_ADDRESS
from data.models import User, UserScan, TokenData, WalletData, TrackingSubscription, KOLWallet
from services.payment import get_plan_payment_details

_db: Optional[Database] = None

def init_database() -> bool:
    """Initialize the database connection and set up indexes"""
    global _db
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI) 
        _db = client[DB_NAME]
        
        # Set up indexes for collections
        # Users collection
        _db.users.create_index([("user_id", ASCENDING)], unique=True)
        
        # User scans collection
        _db.user_scans.create_index([
            ("user_id", ASCENDING),
            ("scan_type", ASCENDING),
            ("date", ASCENDING)
        ], unique=True)
        
        # Token data collection
        _db.token_data.create_index([("address", ASCENDING)], unique=True)
        _db.token_data.create_index([("deployer", ASCENDING)])
        
        # Wallet data collection
        _db.wallet_data.create_index([("address", ASCENDING)], unique=True)
        _db.wallet_data.create_index([("is_kol", ASCENDING)])
        _db.wallet_data.create_index([("is_deployer", ASCENDING)])
        
        # Tracking subscriptions collection
        _db.tracking_subscriptions.create_index([
            ("user_id", ASCENDING),
            ("tracking_type", ASCENDING),
            ("target_address", ASCENDING)
        ], unique=True)
        
        # KOL wallets collection
        _db.kol_wallets.create_index([("address", ASCENDING)], unique=True)
        _db.kol_wallets.create_index([("name", ASCENDING)])
        
        server_info = client.server_info()
        logging.info(f"✅ Successfully connected to MongoDB version: {server_info.get('version')}")
        logging.info(f"✅ Using database: {DB_NAME}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to initialize database: {e}")
        return False

def get_database() -> Database:
    """Get the database instance"""
    global _db
    if _db is None:
        init_database()
    return _db

def get_user(user_id: int) -> Optional[User]:
    """Get a user by ID"""
    db = get_database()
    user_data = db.users.find_one({"user_id": user_id})
    if user_data:
        return User.from_dict(user_data)
    return None

def save_user(user: User) -> None:
    """Save or update a user"""
    db = get_database()
    user_dict = user.to_dict()
    db.users.update_one(
        {"user_id": user.user_id},
        {"$set": user_dict},
        upsert=True
    )

def update_user_activity(user_id: int) -> None:
    """Update user's last active timestamp"""
    db = get_database()
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"last_active": datetime.now()}}
    )

def set_premium_status(user_id: int, is_premium: bool, duration_days: int = 30) -> None:
    """Set a user's premium status"""
    db = get_database()
    premium_until = datetime.now() + timedelta(days=duration_days) if is_premium else None
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "is_premium": is_premium,
            "premium_until": premium_until
        }}
    )

def get_user_scan_count(user_id: int, scan_type: str, date: str) -> int:
    """Get the number of scans a user has performed of a specific type on a date"""
    db = get_database()
    scan_data = db.user_scans.find_one({
        "user_id": user_id,
        "scan_type": scan_type,
        "date": date
    })
    return scan_data.get("count", 0) if scan_data else 0

def increment_user_scan_count(user_id: int, scan_type: str, date: str) -> None:
    """Increment the scan count for a user"""
    db = get_database()
    db.user_scans.update_one(
        {
            "user_id": user_id,
            "scan_type": scan_type,
            "date": date
        },
        {"$inc": {"count": 1}},
        upsert=True
    )

def reset_user_scan_counts() -> None:
    """Reset all user scan counts (typically called daily)"""
    db = get_database()
    today = datetime.now().date().isoformat()
    # Delete all scan records except today's
    db.user_scans.delete_many({"date": {"$ne": today}})

def get_tokendata(address: str) -> Optional[TokenData]:
    """Get token data by address"""
    db = get_database()
    token_data = db.token_data.find_one({"address": address.lower()})
    if token_data:
        return TokenData.from_dict(token_data)
    return None

def save_token_data(token: TokenData) -> None:
    """Save or update token data"""
    db = get_database()
    token_dict = token.to_dict()
    token_dict["address"] = token_dict["address"].lower()  # Normalize address
    token_dict["last_updated"] = datetime.now()
    
    db.token_data.update_one(
        {"address": token_dict["address"]},
        {"$set": token_dict},
        upsert=True
    )

def get_tokens_by_deployer(deployer_address: str) -> List[TokenData]:
    """Get all tokens deployed by a specific address"""
    db = get_database()
    tokens = db.token_data.find({"deployer": deployer_address.lower()})
    return [TokenData.from_dict(token) for token in tokens]

def get_wallet_data(address: str) -> Optional[WalletData]:
    """Get wallet data by address"""
    db = get_database()
    wallet_data = db.wallet_data.find_one({"address": address.lower()})
    if wallet_data:
        return WalletData.from_dict(wallet_data)
    return None

def save_wallet_data(wallet: WalletData) -> None:
    """Save or update wallet data"""
    db = get_database()
    wallet_dict = wallet.to_dict()
    wallet_dict["address"] = wallet_dict["address"].lower()  # Normalize address
    wallet_dict["last_updated"] = datetime.now()
    
    db.wallet_data.update_one(
        {"address": wallet_dict["address"]},
        {"$set": wallet_dict},
        upsert=True
    )

def get_profitable_wallets(days: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get most profitable wallets in the last N days"""
    db = get_database()
    since_date = datetime.now() - timedelta(days=days)
    
    # This is a placeholder - in a real implementation, you would have a collection
    # of wallet transactions or profits to query from
    wallets = db.wallet_data.find({
        "last_updated": {"$gte": since_date},
        "win_rate": {"$gt": 50}  # Only wallets with >50% win rate
    }).sort("win_rate", DESCENDING).limit(limit)
    
    return [WalletData.from_dict(wallet).to_dict() for wallet in wallets]

def get_profitable_deployers(days: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get most profitable token deployer wallets in the last N days"""
    db = get_database()
    since_date = datetime.now() - timedelta(days=days)
    
    # This is a placeholder - in a real implementation, you would have more complex logic
    wallets = db.wallet_data.find({
        "is_deployer": True,
        "last_updated": {"$gte": since_date}
    }).sort("win_rate", DESCENDING).limit(limit)
    
    return [WalletData.from_dict(wallet).to_dict() for wallet in wallets]

def get_kol_wallet(name_or_address: str) -> Optional[KOLWallet]:
    """Get a KOL wallet by name or address"""
    db = get_database()
    # Try to find by name first (case-insensitive)
    kol = db.kol_wallets.find_one({
        "$or": [
            {"name": {"$regex": f"^{name_or_address}$", "$options": "i"}},
            {"address": name_or_address.lower()}
        ]
    })
    
    if kol:
        return KOLWallet.from_dict(kol)
    return None

def get_all_kol_wallets() -> List[KOLWallet]:
    """Get all KOL wallets"""
    db = get_database()
    kols = db.kol_wallets.find().sort("name", ASCENDING)
    return [KOLWallet.from_dict(kol) for kol in kols]

def save_kol_wallet(kol: KOLWallet) -> None:
    """Save or update a KOL wallet"""
    db = get_database()
    kol_dict = kol.to_dict()
    kol_dict["address"] = kol_dict["address"].lower()  # Normalize address
    
    db.kol_wallets.update_one(
        {"address": kol_dict["address"]},
        {"$set": kol_dict},
        upsert=True
    )

def get_user_tracking_subscriptions(user_id: int) -> List[TrackingSubscription]:
    """Get all tracking subscriptions for a user"""
    db = get_database()
    subscriptions = db.tracking_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    })
    return [TrackingSubscription.from_dict(sub) for sub in subscriptions]

def get_all_active_subscriptions_by_type(tracking_type: str) -> List[TrackingSubscription]:
    """Get all active subscriptions of a specific type"""
    db = get_database()
    subscriptions = db.tracking_subscriptions.find({
        "tracking_type": tracking_type,
        "is_active": True
    })
    return [TrackingSubscription.from_dict(sub) for sub in subscriptions]

def get_tracking_subscription(user_id: int, tracking_type: str, target_address: str) -> Optional[TrackingSubscription]:
    """Get a specific tracking subscription"""
    db = get_database()
    subscription = db.tracking_subscriptions.find_one({
        "user_id": user_id,
        "tracking_type": tracking_type,
        "target_address": target_address.lower()
    })
    if subscription:
        return TrackingSubscription.from_dict(subscription)
    return None

def save_tracking_subscription(subscription: TrackingSubscription) -> None:
    """Save or update a tracking subscription"""
    db = get_database()
    sub_dict = subscription.to_dict()
    sub_dict["target_address"] = sub_dict["target_address"].lower()  # Normalize address
    
    db.tracking_subscriptions.update_one(
        {
            "user_id": sub_dict["user_id"],
            "tracking_type": sub_dict["tracking_type"],
            "target_address": sub_dict["target_address"]
        },
        {"$set": sub_dict},
        upsert=True
    )

def delete_tracking_subscription(user_id: int, tracking_type: str, target_address: str) -> None:
    """Delete a tracking subscription"""
    db = get_database()
    db.tracking_subscriptions.delete_one({
        "user_id": user_id,
        "tracking_type": tracking_type,
        "target_address": target_address.lower()
    })

def update_subscription_check_time(subscription_id: str) -> None:
    """Update the last checked time for a subscription"""
    db = get_database()
    db.tracking_subscriptions.update_one(
        {"_id": subscription_id},
        {"$set": {"last_checked": datetime.now()}}
    )

def cleanup_expired_premium() -> None:
    """Remove premium status from users whose premium has expired"""
    db = get_database()
    now = datetime.now()
    db.users.update_many(
        {
            "is_premium": True,
            "premium_until": {"$lt": now}
        },
        {"$set": {
            "is_premium": False,
            "premium_until": None
        }}
    )

def cleanup_old_data(days: int = 30) -> None:
    """Clean up old data that hasn't been updated in a while"""
    db = get_database()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Remove old token data
    db.token_data.delete_many({"last_updated": {"$lt": cutoff_date}})
    
    # Remove old wallet data
    db.wallet_data.delete_many({"last_updated": {"$lt": cutoff_date}})

def get_all_active_tracking_subscriptions() -> List[TrackingSubscription]:
    """Get all active tracking subscriptions across all users"""
    db = get_database()
    subscriptions = db.tracking_subscriptions.find({"is_active": True})
    return [TrackingSubscription.from_dict(sub) for sub in subscriptions]

def get_users_with_expiring_premium(days_left: List[int]) -> List[User]:
    """Get users whose premium subscription is expiring in the specified number of days"""
    db = get_database()
    now = datetime.now()
    
    # Calculate date ranges for the specified days left
    date_ranges = []
    for days in days_left:
        start_date = now + timedelta(days=days)
        end_date = start_date + timedelta(days=1)
        date_ranges.append({"premium_until": {"$gte": start_date, "$lt": end_date}})
    
    # Find users with premium expiring in any of the specified ranges
    users = db.users.find({
        "is_premium": True,
        "$or": date_ranges
    })
    
    return [User.from_dict(user) for user in users]

def get_all_users() -> List[User]:
    """Get all users in the database"""
    db = get_database()
    users = db.users.find()
    return [User.from_dict(user) for user in users]

def get_admin_users() -> List[User]:
    """Get all users with admin privileges"""
    db = get_database()
    admin_users = db.users.find({"is_admin": True})
    return [User.from_dict(user) for user in admin_users]

def set_user_admin_status(user_id: int, is_admin: bool) -> None:
    """Set a user's admin status"""
    db = get_database()
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"is_admin": is_admin}}
    )

def get_user_counts() -> Dict[str, int]:
    """Get user count statistics"""
    db = get_database()
    now = datetime.now()
    
    # Calculate date thresholds
    today_start = datetime.combine(now.date(), datetime.min.time())
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Get counts
    total_users = db.users.count_documents({})
    premium_users = db.users.count_documents({"is_premium": True})
    active_today = db.users.count_documents({"last_active": {"$gte": today_start}})
    active_week = db.users.count_documents({"last_active": {"$gte": week_ago}})
    active_month = db.users.count_documents({"last_active": {"$gte": month_ago}})
    
    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "active_today": active_today,
        "active_week": active_week,
        "active_month": active_month
    }

def update_user_referral_code(user_id: int, referral_code: str) -> None:
    """Update a user's referral code"""
    db = get_database()
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"referral_code": referral_code}}
    )

def record_referral(referrer_id: int, referred_id: int) -> None:
    """Record a referral relationship"""
    db = get_database()
    
    # Create referral record
    db.referrals.update_one(
        {
            "referrer_id": referrer_id,
            "referred_id": referred_id
        },
        {
            "$set": {
                "referrer_id": referrer_id,
                "referred_id": referred_id,
                "date": datetime.now()
            }
        },
        upsert=True
    )
    
    # Update referrer's stats
    db.users.update_one(
        {"user_id": referrer_id},
        {"$inc": {"referral_count": 1}}
    )

def update_user_premium_status(
    user_id: int,
    is_premium: bool,
    premium_until: datetime,
    plan: str,
    payment_currency: str = "eth",
    transaction_id: str = None
) -> None:
    """
    Update a user's premium status in the database and record the transaction
    
    Args:
        user_id: The Telegram user ID
        is_premium: Whether the user has premium status
        premium_until: The date until which premium is active
        plan: The premium plan (weekly or monthly)
        payment_currency: The currency used for payment (eth or bnb)
        transaction_id: The payment transaction ID (optional)
    """
    try:
        # Get database connection
        db = get_database()
        
        # Update user premium status
        db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_premium": is_premium,
                "premium_until": premium_until,
                "premium_plan": plan,
                "payment_currency": payment_currency,
                "last_payment_id": transaction_id,
                "updated_at": datetime.now()
            }}
        )
        
        # Get payment details
        payment_details = get_plan_payment_details(plan, payment_currency)
        
        # Record the transaction
        db.transactions.insert_one({
            "user_id": user_id,
            "type": "premium_purchase",
            "plan_type": plan,
            "currency": payment_details["currency"],  # Already uppercase from get_plan_payment_details
            "amount": payment_details["amount"],
            "duration_days": payment_details["duration_days"],
            "network": payment_details["network"],
            "transaction_id": transaction_id,
            "date": datetime.now()
        })
        
        logging.info(f"Updated premium status for user {user_id}: premium={is_premium}, plan={plan}, currency={payment_currency}, until={premium_until}")
        
    except Exception as e:
        logging.error(f"Error updating user premium status: {e}")
        raise

# token_analysis
async def get_token_first_buyers(token_address: str, chain:str) -> List[Dict[str, Any]]:
    """
    Placeholder function for getting the first buyers data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        List of dictionaries containing first buyer data
    """
    logging.info(f"Placeholder: get_token_first_buyers called for {token_address}")
        
    # Generate some dummy first buyers data
    first_buyers = []
    for i in range(10):
        # Generate a random wallet address
        wallet = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        first_buyers.append({
            "address": wallet,
            "buy_amount": round(random.uniform(1000, 10000), 2),
            "buy_value": round(random.uniform(0.5, 5), 2),
            "pnl": round(random.uniform(-50, 300), 2)
        })
    
    return first_buyers

async def get_token_profitable_wallets(token_address: str, chain:str) -> List[Dict[str, Any]]:
    """
    Placeholder function for getting the most profitable wallets for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        List of dictionaries containing profitable wallet data
    """
    logging.info(f"Placeholder: get_token_profitable_wallets called for {token_address}")
    
    # Generate some dummy profitable wallets data
    profitable_wallets = []
    for i in range(10):
        # Generate a random wallet address
        wallet = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        buy_amount = round(random.uniform(5000, 50000), 2)
        sell_amount = round(buy_amount * random.uniform(0.7, 0.95), 2)
        profit = round(random.uniform(1000, 10000), 2)
        
        profitable_wallets.append({
            "address": wallet,
            "buy_amount": buy_amount,
            "sell_amount": sell_amount,
            "profit": profit,
            "roi": round(random.uniform(50, 500), 2)
        })
    
    return profitable_wallets

async def get_ath_data(token_address: str, chain:str) -> Dict[str, Any]:
    """
    Placeholder function for getting the ATH data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        Dictionary containing token ATH data
    """
    
    logging.info(f"Placeholder: get_ath_data called for {token_address}")
    
    # Generate random token data for demonstration purposes
    token_symbols = ["USDT", "WETH", "PEPE", "SHIB", "DOGE", "LINK", "UNI", "AAVE", "COMP", "SNX"]
    token_names = ["Tether", "Wrapped Ethereum", "Pepe", "Shiba Inu", "Dogecoin", "Chainlink", "Uniswap", "Aave", "Compound", "Synthetix"]
    
    # Pick a random name and symbol
    index = random.randint(0, len(token_symbols) - 1)
    symbol = token_symbols[index]
    name = token_names[index]
    
    # Generate random price and market cap
    current_price = round(random.uniform(0.00001, 100), 6)
    market_cap = round(current_price * random.uniform(1000000, 10000000000), 2)
    
    # Generate random ATH data
    ath_multiplier = random.uniform(1.5, 10)
    ath_price = round(current_price * ath_multiplier, 6)
    ath_market_cap = round(market_cap * ath_multiplier, 2)
    
    # Generate random dates
    now = datetime.now()
    launch_date = (now - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d")
    ath_date = (now - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
    
    # Create ATH data dictionary
    ath_data = {
        "address": token_address,
        "name": name,
        "symbol": symbol,
        "current_price": current_price,
        "current_market_cap": market_cap,
        "holders_count": random.randint(100, 10000),
        "liquidity": round(random.uniform(10000, 1000000), 2),
        "launch_date": launch_date,
        "ath_price": ath_price,
        "ath_date": ath_date,
        "ath_market_cap": ath_market_cap,
        "percent_from_ath": round((current_price / ath_price) * 100, 2),
        "days_since_ath": random.randint(1, 30),
        "ath_volume": round(random.uniform(100000, 10000000), 2)
    }
    
    return ath_data

async def get_deployer_wallet_scan_data(token_address: str, chain:str) -> Dict[str, Any]:
    """
    Placeholder function for getting deployer wallet data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        Dictionary containing deployer wallet data
    """
  
    logging.info(f"Placeholder: get_deployer_wallet_scan_data called for {token_address}")
    
    # Generate a random deployer wallet address
    deployer_address = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
    
    # Generate random token data for demonstration purposes
    now = datetime.now()
    
    # Generate list of tokens deployed by this wallet
    deployed_tokens = []
    for i in range(random.randint(3, 10)):
        token_address = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        token_name = f"Token {i+1}"
        token_symbol = f"TKN{i+1}"
        
        # Generate random price and market cap
        current_price = round(random.uniform(0.00001, 100), 6)
        market_cap = round(current_price * random.uniform(1000000, 10000000000), 2)
        
        # Generate random ATH data
        ath_multiplier = random.uniform(1.5, 10)
        ath_price = round(current_price * ath_multiplier, 6)
        ath_market_cap = round(market_cap * ath_multiplier, 2)
        
        # Generate random dates
        deploy_date = (now - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d")
        
        # Calculate x-multiplier (ATH price / initial price)
        initial_price = round(current_price / random.uniform(1, ath_multiplier), 8)
        x_multiplier = round(ath_price / initial_price, 2)
        
        # Create token data
        token_data = {
            "address": token_address,
            "name": token_name,
            "symbol": token_symbol,
            "current_price": current_price,
            "current_market_cap": market_cap,
            "ath_price": ath_price,
            "ath_market_cap": ath_market_cap,
            "deploy_date": deploy_date,
            "initial_price": initial_price,
            "x_multiplier": f"{x_multiplier}x",
            "status": random.choice(["Active", "Abandoned", "Rugpull", "Successful"])
        }
        
        deployed_tokens.append(token_data)
    
    # Sort by deploy date (newest first)
    deployed_tokens.sort(key=lambda x: x["deploy_date"], reverse=True)
    
    # Create deployer wallet data
    deployer_data = {
        "deployer_address": deployer_address,
        "tokens_deployed": len(deployed_tokens),
        "first_deployment_date": deployed_tokens[-1]["deploy_date"],
        "last_deployment_date": deployed_tokens[0]["deploy_date"],
        "success_rate": round(random.uniform(10, 100), 2),
        "avg_roi": round(random.uniform(-50, 500), 2),
        "rugpull_count": random.randint(0, 3),
        "risk_level": random.choice(["Low", "Medium", "High", "Very High"]),
        "deployed_tokens": deployed_tokens
    }
    
    return deployer_data

async def get_token_top_holders(token_address: str, chain:str) -> List[Dict[str, Any]]:
    """
    Placeholder function for getting top holders data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        List of dictionaries containing top holder data
    """
    logging.info(f"Placeholder: get_token_holders called for {token_address}")
    
    # Generate some dummy top holders data
    top_holders = []
    total_supply = random.uniform(1000000, 1000000000)
    
    # Generate top 10 holders
    for i in range(10):
        # Generate a random wallet address
        wallet = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        # Calculate percentage (decreasing as rank increases)
        percentage = round(random.uniform(30, 5) / (i + 1), 2)
        
        # Calculate token amount based on percentage
        token_amount = round((percentage / 100) * total_supply, 2)
        
        # Calculate USD value
        token_price = random.uniform(0.0001, 0.1)
        usd_value = round(token_amount * token_price, 2)
        
        # Determine if it's a DEX or CEX
        is_exchange = random.choice([True, False])
        exchange_type = random.choice(["Uniswap V3", "Uniswap V2", "SushiSwap", "PancakeSwap"]) if is_exchange else None
        
        # Determine wallet type
        wallet_type = "Exchange" if is_exchange else random.choice(["Whale", "Investor", "Team", "Unknown"])
        
        top_holders.append({
            "rank": i + 1,
            "address": wallet,
            "token_amount": token_amount,
            "percentage": percentage,
            "usd_value": usd_value,
            "wallet_type": wallet_type,
            "exchange_name": exchange_type,
            "holding_since": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            "last_transaction": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        })
    
    return top_holders

async def get_high_net_worth_holders(token_address: str, chain:str) -> List[Dict[str, Any]]:
    """
    Placeholder function for getting high net worth holders data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        List of dictionaries containing high net worth holder data
    """
    logging.info(f"Placeholder: get_high_net_worth_holders called for {token_address}")
    
    # Generate some dummy high net worth holders data
    high_net_worth_holders = []
    
    # Generate 8-12 high net worth holders
    for i in range(random.randint(8, 12)):
        # Generate a random wallet address
        wallet = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        # Calculate token amount
        token_amount = round(random.uniform(100000, 10000000), 2)
        
        # Calculate USD value (minimum $10,000)
        token_price = random.uniform(0.001, 0.1)
        usd_value = max(10000, round(token_amount * token_price, 2))
        
        # Generate portfolio data
        portfolio_size = random.randint(3, 20)
        avg_holding_time = random.randint(30, 365)
        
        # Generate success metrics
        success_rate = round(random.uniform(50, 95), 2)
        avg_roi = round(random.uniform(20, 500), 2)
        
        high_net_worth_holders.append({
            "address": wallet,
            "token_amount": token_amount,
            "usd_value": usd_value,
            "portfolio_size": portfolio_size,  # Number of different tokens held
            "avg_holding_time": avg_holding_time,  # Average days holding tokens
            "success_rate": success_rate,  # Percentage of profitable trades
            "avg_roi": avg_roi,  # Average ROI percentage
            "first_seen": (datetime.now() - timedelta(days=random.randint(100, 1000))).strftime("%Y-%m-%d"),
            "last_transaction": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        })
    
    # Sort by USD value (highest first)
    high_net_worth_holders.sort(key=lambda x: x["usd_value"], reverse=True)
    
    return high_net_worth_holders


# wallet analysis
async def get_wallet_data(wallet_address: str, chain: str = "eth") -> dict:
    """
    Get data for a wallet address
    
    Args:
        wallet_address: The wallet address to analyze
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        Dictionary containing wallet data
    """
    logging.info(f"Placeholder: get_wallet_data called for {wallet_address} on {chain}")
    
    # Generate random wallet data
    now = datetime.now()
    
    # Create wallet data dictionary
    wallet_data = {
        "address": wallet_address,
        "first_transaction_date": (now - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
        "total_transactions": random.randint(10, 1000),
        "total_tokens_held": random.randint(5, 50),
        "estimated_value": round(random.uniform(1000, 1000000), 2),
        "chain": chain,  # Include the chain in the response
        "transaction_count": {
            "buys": random.randint(10, 500),
            "sells": random.randint(10, 300),
            "transfers": random.randint(5, 100),
            "swaps": random.randint(5, 100)
        },
        "profit_stats": {
            "total_profit_usd": round(random.uniform(-10000, 100000), 2),
            "win_rate": round(random.uniform(30, 90), 2),
            "avg_holding_time_days": round(random.uniform(1, 30), 2),
            "best_trade_profit": round(random.uniform(1000, 50000), 2),
            "worst_trade_loss": round(random.uniform(-20000, -100), 2)
        }
    }
    
    return wallet_data

async def get_wallet_holding_duration(wallet_address: str, chain: str = "eth") -> dict:
    """
    Get holding duration data for a wallet
    
    Args:
        wallet_address: The wallet address to analyze
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        Dictionary containing holding duration data
    """
  
    logging.info(f"Placeholder: get_wallet_holding_duration called for {wallet_address} on {chain}")
    
    # Get basic wallet data
    wallet_data = await get_wallet_data(wallet_address, chain)
    
    # Generate holding duration data
    holding_data = {
        "wallet_address": wallet_address,
        "avg_holding_time_days": wallet_data["profit_stats"]["avg_holding_time_days"],
        "chain": chain,
        "tokens_analyzed": random.randint(10, 50),
        "holding_distribution": {
            "less_than_1_day": round(random.uniform(5, 30), 2),
            "1_to_7_days": round(random.uniform(20, 50), 2),
            "7_to_30_days": round(random.uniform(10, 40), 2),
            "more_than_30_days": round(random.uniform(5, 30), 2)
        },
        "token_examples": []
    }
    
    # Generate example tokens with holding durations
    token_names = ["Ethereum", "Uniswap", "Chainlink", "Aave", "Compound", "Synthetix", "Pepe", "Shiba Inu"]
    token_symbols = ["ETH", "UNI", "LINK", "AAVE", "COMP", "SNX", "PEPE", "SHIB"]
    
    for i in range(5):
        idx = random.randint(0, len(token_names) - 1)
        holding_days = round(random.uniform(0.5, 60), 1)
        
        token_example = {
            "name": token_names[idx],
            "symbol": token_symbols[idx],
            "address": "0x" + ''.join(random.choices('0123456789abcdef', k=40)),
            "holding_days": holding_days,
            "profit": round(random.uniform(-5000, 10000), 2)
        }
        
        holding_data["token_examples"].append(token_example)
    
    return holding_data

async def get_wallet_most_profitable_in_period(days: int = 30, limit: int = 10, chain: str = "eth") -> list:
    """
    Get most profitable wallets in a specific period
    
    Args:
        days: Number of days to analyze
        limit: Maximum number of wallets to return
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        List of dictionaries containing profitable wallet data
    """
    logging.info(f"Placeholder: get_wallet_most_profitable_in_period called for {days} days on {chain}")
    
    # Generate dummy profitable wallets data
    profitable_wallets = []
    
    for i in range(limit):
        wallet_address = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        wallet = {
            "address": wallet_address,
            "total_profit": round(random.uniform(1000, 100000), 2),
            "win_rate": round(random.uniform(50, 95), 2),
            "trades_count": random.randint(10, 100),
            "avg_profit_per_trade": round(random.uniform(100, 2000), 2),
            "chain": chain,
            "period_days": days
        }
        
        profitable_wallets.append(wallet)
    
    # Sort by total profit (descending)
    profitable_wallets.sort(key=lambda x: x["total_profit"], reverse=True)
    
    return profitable_wallets

async def get_most_profitable_token_deployer_wallets(days: int = 30, limit: int = 10, chain: str = "eth") -> list:
    """
    Get most profitable token deployer wallets
    
    Args:
        days: Number of days to analyze
        limit: Maximum number of wallets to return
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        List of dictionaries containing profitable deployer wallet data
    """   
    logging.info(f"Placeholder: get_most_profitable_token_deployer_wallets called for {days} days on {chain}")
    
    # Generate dummy deployer wallets data
    deployer_wallets = []
    
    for i in range(limit):
        wallet_address = "0x" + ''.join(random.choices('0123456789abcdef', k=40))
        
        wallet = {
            "address": wallet_address,
            "tokens_deployed": random.randint(1, 20),
            "successful_tokens": random.randint(1, 10),
            "total_profit": round(random.uniform(5000, 500000), 2),
            "success_rate": round(random.uniform(20, 90), 2),
            "avg_roi": round(random.uniform(50, 1000), 2),
            "chain": chain,
            "period_days": days
        }
        
        deployer_wallets.append(wallet)
    
    # Sort by total profit (descending)
    deployer_wallets.sort(key=lambda x: x["total_profit"], reverse=True)
    
    return deployer_wallets

async def get_tokens_deployed_by_wallet(wallet_address: str, chain: str = "eth") -> list:
    """
    Get tokens deployed by a wallet
    
    Args:
        wallet_address: The wallet address to analyze
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        List of dictionaries containing token data
    """   
    logging.info(f"Placeholder: get_tokens_deployed_by_wallet called for {wallet_address} on {chain}")
    
    # Generate dummy tokens data
    tokens = []
    now = datetime.now()
    
    token_names = ["Super", "Mega", "Ultra", "Hyper", "Rocket", "Moon", "Star", "Galaxy"]
    token_suffixes = ["Token", "Coin", "Finance", "Cash", "Swap", "Yield", "Dao", "AI"]
    
    for i in range(random.randint(3, 10)):
        # Generate random token name and symbol
        name_prefix = random.choice(token_names)
        name_suffix = random.choice(token_suffixes)
        token_name = f"{name_prefix} {name_suffix}"
        token_symbol = f"{name_prefix[:1]}{name_suffix[:1]}".upper()
        
        # Generate random dates and prices
        deploy_date = (now - timedelta(days=random.randint(10, 180))).strftime("%Y-%m-%d")
        current_price = round(random.uniform(0.00001, 10), 6)
        
        # Generate random market caps
        current_market_cap = round(current_price * random.uniform(100000, 10000000), 2)
        ath_multiplier = random.uniform(1.5, 20)
        ath_market_cap = round(current_market_cap * ath_multiplier, 2)
        
        token = {
            "address": "0x" + ''.join(random.choices('0123456789abcdef', k=40)),
            "name": token_name,
            "symbol": token_symbol,
            "deploy_date": deploy_date,
            "current_price": current_price,
            "current_market_cap": current_market_cap,
            "ath_market_cap": ath_market_cap,
            "ath_multiplier": round(ath_multiplier, 2),
            "chain": chain,
            "deployer": wallet_address
        }
        
        tokens.append(token)
    
    # Sort by deploy date (newest first)
    tokens.sort(key=lambda x: x["deploy_date"], reverse=True)
    
    return tokens


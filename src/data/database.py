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

from api.token_api import *
from api.wallet_api import *

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
        
    response = await fetch_first_buyers(chain, token_address)

    first_buyers = response.get("unique_buyers")
    
    return first_buyers[:5]

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
    response = await fetch_token_profitable_wallets(chain, token_address)

    profitable_wallets = response.get("wallets")
    
    return profitable_wallets[:5]

async def get_ath_data(token_address: str, chain:str) -> Dict[str, Any]:
    """
    Placeholder function for getting the ATH data for a specific token
    
    Args:
        token_address: The token contract address
    
    Returns:
        Dictionary containing token ATH data
    """
    
    logging.info(f"Placeholder: get_ath_data called for {token_address}")

    response = await fetch_market_cap(chain, token_address.lower())

    age = response.get("age")
    cur_mcap = response.get("current_mc")
    ath_mcap = response.get("max_mc")
    ath_date = response.get("ath_date")
    # Create ATH data dictionary
    ath_data = {
        "age": age,
        "cur_mcap": round(cur_mcap, 2),
        "ath_mcap": round(ath_mcap, 2),
        "ath_date": ath_date,
    }
    
    return ath_data

async def get_deployer_wallet_scan_data(token_address: str, chain:str) -> Dict[str, Any]:
    """
    Function for getting deployer wallet data for a specific token
    
    Args:
        token_address: The token contract address
        chain: The blockchain network (eth, base, bsc)
    
    Returns:
        Dictionary containing deployer wallet data
    """
    logging.info(f"Getting deployer wallet scan data for {token_address} on {chain}")
    
    from utils import get_token_info
    
    try:
        # Fetch token deployer projects data from API
        response = await fetch_token_deployer_projects(chain, token_address)
        
        if not response:
            logging.warning(f"No deployer data found for token {token_address} on {chain}")
            return None
        
        # Extract data from response
        token_address = response.get("token_address")
        deployer_address = response.get("deployer_address")
        chain_name = response.get("chain")
        related_tokens = response.get("related_tokens", [])
        total_count = response.get("total_count", 0)
        
        # Process related tokens data
        deployed_tokens = []
        for token in related_tokens:
            contract_address = token.get("contract_address")
            
            # Get token name and symbol using get_token_info
            token_info = await get_token_info(contract_address, chain)
            
            # Get market cap data using fetch_market_cap
            market_cap_data = await fetch_market_cap(chain, contract_address)
            
            # Extract market cap information
            current_mc = market_cap_data.get("current_mc", 0)
            ath_mc = market_cap_data.get("max_mc", 0)
            ath_date = market_cap_data.get("ath_date", "")
            
            # Create token data object with available information
            token_data = {
                "address": contract_address,
                "name": token_info.get("name", "Unknown Token") if token_info else "Unknown Token",
                "symbol": token_info.get("symbol", "???") if token_info else "???",
                "deploy_date": token.get("deployment_time_readable", "").split("T")[0],
                "current_market_cap": current_mc,
                "ath_market_cap": ath_mc,
                "ath_date": ath_date,
                "deployment_tx": token.get("transaction_hash"),
            }
            
            # Calculate x-multiplier if we have both current and ATH market caps
            if current_mc and ath_mc and ath_mc > 0:
                token_data["x_multiplier"] = f"{round(ath_mc / current_mc, 2)}x"
            else:
                token_data["x_multiplier"] = "N/A"
                
            deployed_tokens.append(token_data)
        
        # Sort by deploy date (newest first)
        deployed_tokens.sort(key=lambda x: x.get("deploy_date", ""), reverse=True)

        # Create deployer wallet data
        deployer_data = {
            "deployer_address": deployer_address,
            "tokens_deployed": total_count,
            "deployed_tokens": deployed_tokens
        }
        
        return deployer_data
        
    except Exception as e:
        logging.error(f"Error getting deployer wallet scan data: {e}")
        return None

async def get_token_top_holders(token_address: str, chain: str) -> List[Dict[str, Any]]:
    """
    Get top holders data for a specific token
    
    Args:
        token_address: The token contract address
        chain: The blockchain network
    
    Returns:
        List of dictionaries containing top holder data
    """
    logging.info(f"Getting top holders for {token_address} on {chain}")
    
    # Fetch data from API or service
    response = await fetch_token_holders(chain, token_address)
    
    top_holders = []
    
    # Process the response data
    for i, holder in enumerate(response[:10], 1):  # Limit to top 10 holders
        # Extract and format the most important fields
        wallet_type = "Exchange" if any(tag in holder.get('tags', []) for tag in ["exchange", "cex", "dex"]) else "Whale"
        
        # Calculate holding since date from timestamp if available
        holding_since = "N/A"
        if holder.get('start_holding_at'):
            try:
                holding_since = datetime.fromtimestamp(holder['start_holding_at']).strftime("%Y-%m-%d")
            except:
                pass
        
        # Format last active date
        last_transaction = "N/A"
        if holder.get('last_active_timestamp'):
            try:
                last_transaction = datetime.fromtimestamp(holder['last_active_timestamp']).strftime("%Y-%m-%d")
            except:
                pass
        
        top_holders.append({
            "rank": i,
            "address": holder.get('address', ''),
            "token_amount": holder.get('amount_cur', 0),
            "percentage": holder.get('amount_percentage', 0) * 100,  # Convert to percentage
            "usd_value": holder.get('usd_value', 0),
            "wallet_type": wallet_type,
            "exchange_name": holder.get('name'),
            "holding_since": holding_since,
            "last_transaction": last_transaction
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
    
    now = datetime.now()
    
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

async def get_wallet_most_profitable_in_period(days: int = 30, limit: int = 10, chain: str = "eth") -> List[Dict[str, Any]]:
    """
    Get the most profitable wallets in a specific period
    
    Args:
        days: Number of days to look back
        limit: Maximum number of wallets to return
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        List of dictionaries containing wallet data
    """
    logging.info(f"Getting most profitable wallets for {days} days, limit {limit}, chain {chain}")
    
    try:
        response = await fetch_profitable_defi_wallets(chain)
        
        # Check if we have data
        if not response or "periods" not in response:
            logging.warning(f"No data returned from fetch_profitable_defi_wallets for chain {chain}")
            return []
        
        # Find the period that matches the requested days
        wallets = []
        for period in response.get("periods", []):
            if period.get("days") == days:
                wallets = period.get("wallets", [])
                break
        
        # If no matching period found or no wallets in that period
        if not wallets:
            logging.info(f"No wallets found for period {days} days on chain {chain}")
            return []
        
        # Transform the data to match our expected format
        formatted_wallets = []
        for wallet in wallets[:limit]:
            formatted_wallets.append({
                "address": wallet.get("wallet_address"),
                "total_profit": wallet.get("total_profit", 0),
                "win_rate": wallet.get("win_rate", 0) * 100,  # Convert to percentage
                "trades_count": wallet.get("total_trades", 0),
                "period_days": days,
                "chain": chain,
                "total_buy_usd": wallet.get("total_buy_usd", 0),
                "total_sell_usd": wallet.get("total_sell_usd", 0),
                "total_wins": wallet.get("total_wins", 0),
                "total_losses": wallet.get("total_losses", 0),
                "pnl_ratio": wallet.get("pnl_ratio", 0)
            })
        
        logging.info(f"Returning {len(formatted_wallets)} wallets")
        return formatted_wallets
        
    except Exception as e:
        logging.error(f"Error getting most profitable wallets: {e}", exc_info=True)
        return []

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
    logging.info(f"Getting most profitable token deployer wallets for {days} days on {chain}")
    
    try:
        # Fetch data from API
        response = await fetch_profitable_deployers(chain)
        
        # Check if we have data
        if not response or "periods" not in response:
            logging.warning(f"No data returned from fetch_profitable_deployer_wallets for chain {chain}")
            return []
        
        # Find the period that matches the requested days
        wallets = []
        for period in response.get("periods", []):
            if period.get("days") == days:
                wallets = period.get("wallets", [])
                break
        
        # If no matching period found or no wallets in that period
        if not wallets:
            logging.info(f"No deployer wallets found for period {days} days on chain {chain}")
            return []
        
        # Transform the data to match our expected format
        formatted_wallets = []
        for wallet in wallets[:limit]:
            formatted_wallets.append({
                "address": wallet.get("wallet_address"),
                "successful_tokens": wallet.get("total_wins", 0),
                "total_profit": wallet.get("total_profit", 0),
                "chain": chain,
                "period_days": days,
                "total_buy_usd": wallet.get("total_buy_usd", 0),
                "total_sell_usd": wallet.get("total_sell_usd", 0),
                "total_trades": wallet.get("total_trades", 0),
                "total_wins": wallet.get("total_wins", 0),
                "total_losses": wallet.get("total_losses", 0),
                "win_rate": wallet.get("win_rate", 0)
            })
        
        # Sort by total profit (descending)
        formatted_wallets.sort(key=lambda x: x["total_profit"], reverse=True)
        
        logging.info(f"Returning {len(formatted_wallets)} deployer wallets")
        return formatted_wallets
        
    except Exception as e:
        logging.error(f"Error getting most profitable token deployer wallets: {e}", exc_info=True)
        return []

async def get_wallet_holding_duration(wallet_address: str, chain: str = "eth") -> dict:
    """
    Get holding duration data for a wallet
    
    Args:
        wallet_address: The wallet address to analyze
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        Dictionary containing holding duration data
    """
    logging.info(f"Getting holding duration data for wallet {wallet_address} on {chain}")
    
    try:
        # Fetch data from API
        response = await fetch_wallet_holding_time(chain, wallet_address)
        
        if not response or "wallet_address" not in response:
            logging.warning(f"No holding duration data found for wallet {wallet_address} on {chain}")
            return {
                "wallet_address": wallet_address,
                "chain": chain,
                "error": "No holding duration data available"
            }
        
        # Extract holding times data
        holding_times = response.get("holding_times", {})
        tokens_info = response.get("tokens", {})
        total_tokens = response.get("total_tokens", 0)
        
        # Get shortest and longest hold token info
        shortest_hold_token = tokens_info.get("shortest_hold", {})
        longest_hold_token = tokens_info.get("longest_hold", {})
        
        # Create holding duration data object
        holding_data = {
            "wallet_address": wallet_address,
            "chain": chain,
            "total_tokens_analyzed": total_tokens,
            "avg_holding_time_days": holding_times.get("average", {}).get("formatted", "N/A"),
            "shortest_holding_time": holding_times.get("shortest", {}).get("formatted", "N/A"),
            "longest_holding_time": holding_times.get("longest", {}).get("formatted", "N/A"),
            "shortest_hold_token": {
                "address": shortest_hold_token.get("address", "N/A"),
                "symbol": shortest_hold_token.get("symbol", "Unknown")
            },
            "longest_hold_token": {
                "address": longest_hold_token.get("address", "N/A"),
                "symbol": longest_hold_token.get("symbol", "Unknown")
            }
        }
        
        logging.info(f"Successfully retrieved holding duration data for wallet {wallet_address}")
        return holding_data
        
    except Exception as e:
        logging.error(f"Error getting wallet holding duration: {e}")
        return {
            "wallet_address": wallet_address,
            "chain": chain,
            "error": f"Failed to retrieve holding duration data: {str(e)}"
        }

async def get_tokens_deployed_by_wallet(wallet_address: str, chain: str = "eth") -> list:
    """
    Get tokens deployed by a wallet
    
    Args:
        wallet_address: The wallet address to analyze
        chain: The blockchain network (eth, base, bsc)
        
    Returns:
        List of dictionaries containing token data
    """   
    logging.info(f"Getting tokens deployed by wallet {wallet_address} on {chain}")
    
    from utils import get_token_info
    
    try:
        # Fetch data from API
        response = await fetch_wallet_deployed_tokens(chain, wallet_address)
        
        if not response or "tokens_deployed" not in response:
            logging.warning(f"No deployed tokens found for wallet {wallet_address} on {chain}")
            return []
        
        # Extract deployed tokens from response
        deployed_tokens_raw = response.get("tokens_deployed", [])
        total_count = response.get("total_count", 0)
        
        # Process each token to get additional information
        tokens = []
        for token in deployed_tokens_raw:
            contract_address = token.get("contract_address")
            
            # Get token name and symbol using get_token_info
            token_info = await get_token_info(contract_address, chain)
            
            # Get market cap data using fetch_market_cap
            market_cap_data = await fetch_market_cap(chain, contract_address)
            
            # Extract market cap information
            current_mc = market_cap_data.get("current_mc", 0) if market_cap_data else 0
            ath_mc = market_cap_data.get("max_mc", 0) if market_cap_data else 0
            ath_date = market_cap_data.get("ath_date", "") if market_cap_data else ""
            
            # Calculate token price if available
            current_price = market_cap_data.get("current_price", 0) if market_cap_data else 0
            
            # Create token data object with available information
            token_data = {
                "address": contract_address,
                "name": token_info.get("name", "Unknown Token") if token_info else "Unknown Token",
                "symbol": token_info.get("symbol", "???") if token_info else "???",
                "deploy_date": token.get("deployment_time_readable", "").split(" ")[0],
                "current_price": current_price,
                "current_market_cap": current_mc,
                "ath_market_cap": ath_mc,
                "ath_date": ath_date,
                "deployment_tx": token.get("transaction_hash")
            }
            
            # Calculate ATH multiplier if we have both current and ATH market caps
            if current_mc and ath_mc and current_mc > 0:
                token_data["ath_multiplier"] = round(ath_mc / current_mc, 2)
            else:
                token_data["ath_multiplier"] = "N/A"
                
            tokens.append(token_data)
        
        # Sort by deploy date (newest first)
        tokens.sort(key=lambda x: x.get("deploy_date", ""), reverse=True)
        
        logging.info(f"Found {len(tokens)} tokens deployed by wallet {wallet_address}")
        return tokens
        
    except Exception as e:
        logging.error(f"Error getting tokens deployed by wallet: {e}")
        return []

# kol wallet profitability
async def get_kol_wallet_profitability(days: int, limit: int, chain: str = "eth", kol_name: str = None) -> list:
    """
    Get KOL wallet profitability data (DUMMY IMPLEMENTATION)
    
    Args:
        days: Number of days to analyze
        limit: Maximum number of results to return
        chain: Blockchain to analyze
        kol_name: Name of the specific KOL to filter by (optional)
        
    Returns:
        List of KOL wallet profitability data
    """

    # List of mock KOL names
    kol_names = [
        "Vitalik Buterin", "CZ Binance", "SBF", "Arthur Hayes", 
        "Justin Sun", "Elon Musk", "Crypto Cobain", "DeFi Dad",
        "Crypto Messiah", "Crypto Whale", "DegenSpartan", "Tetranode",
        "Hsaka", "Cobie", "DCinvestor", "ChainLinkGod"
    ]
    
    # Generate random KOL wallet data
    kol_wallets = []
    
    # If kol_name is provided, filter the list to only include that name (case-insensitive)
    if kol_name:
        filtered_names = [name for name in kol_names if kol_name.lower() in name.lower()]
        # If no match found, add the provided name to ensure we return something
        if not filtered_names and kol_name.strip():
            filtered_names = [kol_name]
        kol_names = filtered_names
    
    for i in range(min(len(kol_names), limit + 5)):  # Generate a few extra to sort later
        # Create base wallet data
        total_profit = random.uniform(10000, 1000000)
        win_rate = random.uniform(40, 95)
        
        # Generate random address
        address = "0x" + "".join(random.choice("0123456789abcdef") for _ in range(40))
        
        # Calculate period profit based on days
        if days == 1:
            period_profit = total_profit * random.uniform(0.01, 0.1)  # 1-10% of total profit
        elif days == 7:
            period_profit = total_profit * random.uniform(0.1, 0.4)   # 10-40% of total profit
        else:  # 30 days
            period_profit = total_profit * random.uniform(0.4, 1.0)   # 40-100% of total profit
        
        # Generate recent trades
        recent_trades = []
        for j in range(random.randint(3, 8)):
            trade_date = datetime.now() - timedelta(days=random.randint(0, days))
            token_names = ["ETH", "BTC", "LINK", "UNI", "AAVE", "MKR", "SNX", "YFI", "COMP", "SUSHI"]
            action = "Buy" if random.random() > 0.4 else "Sell"
            
            recent_trades.append({
                "token": random.choice(token_names),
                "action": action,
                "amount": round(random.uniform(0.1, 100), 2),
                "value": round(random.uniform(1000, 50000), 2),
                "date": trade_date.strftime("%Y-%m-%d %H:%M")
            })
        
        # Create wallet object
        wallet = {
            "name": kol_names[i] if i < len(kol_names) else f"Unknown KOL {i}",
            "address": address,
            "total_profit": total_profit,
            "period_profit": period_profit,
            "win_rate": round(win_rate, 1),
            "total_trades": random.randint(50, 500),
            "avg_position_size": round(random.uniform(5000, 100000), 2),
            "chain": chain,
            "period": days,
            "recent_trades": recent_trades
        }
        
        kol_wallets.append(wallet)
    
    # Sort by period profit
    kol_wallets.sort(key=lambda x: x.get("period_profit", 0), reverse=True)
    
    # Limit results
    return kol_wallets[:limit]

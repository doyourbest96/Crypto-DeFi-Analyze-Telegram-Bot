import logging
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection

from config import MONGODB_URI, DB_NAME
from data.models import User, UserScan, TokenData, WalletData, TrackingSubscription, KOLWallet

# Global database connection
_db: Optional[Database] = None

def init_database() -> None:
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
        
        logging.info("Database connection initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        raise

def get_database() -> Database:
    """Get the database instance"""
    global _db
    if _db is None:
        init_database()
    return _db

# User operations
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

# User scan tracking operations
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

# Token data operations
def get_token_data(address: str) -> Optional[TokenData]:
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

# Wallet data operations
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

# KOL wallet operations
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

# Tracking subscription operations
def get_user_tracking_subscriptions(user_id: int) -> List[TrackingSubscription]:
    """Get all tracking subscriptions for a user"""
    db = get_database()
    subscriptions = db.tracking_subscriptions.find({
        "user_id": user_id,
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

def get_all_active_subscriptions_by_type(tracking_type: str) -> List[TrackingSubscription]:
    """Get all active subscriptions of a specific type"""
    db = get_database()
    subscriptions = db.tracking_subscriptions.find({
        "tracking_type": tracking_type,
        "is_active": True
    })
    return [TrackingSubscription.from_dict(sub) for sub in subscriptions]

def update_subscription_check_time(subscription_id: str) -> None:
    """Update the last checked time for a subscription"""
    db = get_database()
    db.tracking_subscriptions.update_one(
        {"_id": subscription_id},
        {"$set": {"last_checked": datetime.now()}}
    )

# Cleanup and maintenance functions
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

from datetime import datetime
from typing import List, Dict, Optional, Any, Union

class User:
    """User model representing a bot user"""
    def __init__(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_premium: bool = False,
        premium_until: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_premium = is_premium
        self.premium_until = premium_until
        self.created_at = created_at or datetime.now()
        self.last_active = last_active or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_premium": self.is_premium,
            "premium_until": self.premium_until,
            "created_at": self.created_at,
            "last_active": self.last_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user object from dictionary"""
        return cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            is_premium=data.get("is_premium", False),
            premium_until=data.get("premium_until"),
            created_at=data.get("created_at"),
            last_active=data.get("last_active")
        )


class UserScan:
    """Model for tracking user scan usage"""
    def __init__(
        self,
        user_id: int,
        scan_type: str,  # 'token_scan', 'wallet_scan', etc.
        date: str,  # ISO format date string
        count: int = 0
    ):
        self.user_id = user_id
        self.scan_type = scan_type
        self.date = date
        self.count = count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scan object to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "scan_type": self.scan_type,
            "date": self.date,
            "count": self.count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserScan':
        """Create scan object from dictionary"""
        return cls(
            user_id=data["user_id"],
            scan_type=data["scan_type"],
            date=data["date"],
            count=data["count"]
        )


class TokenData:
    """Model for cached token data"""
    def __init__(
        self,
        address: str,
        name: Optional[str] = None,
        symbol: Optional[str] = None,
        deployer: Optional[str] = None,
        deployment_date: Optional[datetime] = None,
        current_price: Optional[float] = None,
        current_market_cap: Optional[float] = None,
        ath_market_cap: Optional[float] = None,
        ath_date: Optional[datetime] = None,
        last_updated: Optional[datetime] = None
    ):
        self.address = address
        self.name = name
        self.symbol = symbol
        self.deployer = deployer
        self.deployment_date = deployment_date
        self.current_price = current_price
        self.current_market_cap = current_market_cap
        self.ath_market_cap = ath_market_cap
        self.ath_date = ath_date
        self.last_updated = last_updated or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token data to dictionary for database storage"""
        return {
            "address": self.address,
            "name": self.name,
            "symbol": self.symbol,
            "deployer": self.deployer,
            "deployment_date": self.deployment_date,
            "current_price": self.current_price,
            "current_market_cap": self.current_market_cap,
            "ath_market_cap": self.ath_market_cap,
            "ath_date": self.ath_date,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenData':
        """Create token data object from dictionary"""
        return cls(
            address=data["address"],
            name=data.get("name"),
            symbol=data.get("symbol"),
            deployer=data.get("deployer"),
            deployment_date=data.get("deployment_date"),
            current_price=data.get("current_price"),
            current_market_cap=data.get("current_market_cap"),
            ath_market_cap=data.get("ath_market_cap"),
            ath_date=data.get("ath_date"),
            last_updated=data.get("last_updated")
        )


class WalletData:
    """Model for cached wallet data"""
    def __init__(
        self,
        address: str,
        name: Optional[str] = None,  # For KOL wallets
        is_kol: bool = False,
        is_deployer: bool = False,
        tokens_deployed: Optional[List[str]] = None,
        avg_holding_time: Optional[int] = None,  # in seconds
        total_trades: Optional[int] = None,
        win_rate: Optional[float] = None,
        last_updated: Optional[datetime] = None
    ):
        self.address = address
        self.name = name
        self.is_kol = is_kol
        self.is_deployer = is_deployer
        self.tokens_deployed = tokens_deployed or []
        self.avg_holding_time = avg_holding_time
        self.total_trades = total_trades
        self.win_rate = win_rate
        self.last_updated = last_updated or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert wallet data to dictionary for database storage"""
        return {
            "address": self.address,
            "name": self.name,
            "is_kol": self.is_kol,
            "is_deployer": self.is_deployer,
            "tokens_deployed": self.tokens_deployed,
            "avg_holding_time": self.avg_holding_time,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WalletData':
        """Create wallet data object from dictionary"""
        return cls(
            address=data["address"],
            name=data.get("name"),
            is_kol=data.get("is_kol", False),
            is_deployer=data.get("is_deployer", False),
            tokens_deployed=data.get("tokens_deployed", []),
            avg_holding_time=data.get("avg_holding_time"),
            total_trades=data.get("total_trades"),
            win_rate=data.get("win_rate"),
            last_updated=data.get("last_updated")
        )


class TrackingSubscription:
    """Model for tracking subscriptions"""
    def __init__(
        self,
        user_id: int,
        tracking_type: str,  # 'token_holders', 'wallet_deployment', 'wallet_trades'
        target_address: str,
        created_at: Optional[datetime] = None,
        last_checked: Optional[datetime] = None,
        is_active: bool = True,
        metadata=None
    ):
        self.user_id = user_id
        self.tracking_type = tracking_type
        self.target_address = target_address
        self.created_at = created_at or datetime.now()
        self.last_checked = last_checked or datetime.now()
        self.is_active = is_active
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracking subscription to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "tracking_type": self.tracking_type,
            "target_address": self.target_address,
            "created_at": self.created_at,
            "last_checked": self.last_checked,
            "is_active": self.is_active,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackingSubscription':
        """Create tracking subscription object from dictionary"""
        return cls(
            user_id=data["user_id"],
            tracking_type=data["tracking_type"],
            target_address=data["target_address"],
            created_at=data.get("created_at"),
            last_checked=data.get("last_checked"),
            is_active=data.get("is_active", True),
            metadata=data.get("metadata", {})
        )


class KOLWallet:
    """Model for KOL (Key Opinion Leader) wallets"""
    def __init__(
        self,
        address: str,
        name: str,
        description: Optional[str] = None,
        social_links: Optional[Dict[str, str]] = None,
        added_at: Optional[datetime] = None
    ):
        self.address = address
        self.name = name
        self.description = description
        self.social_links = social_links or {}
        self.added_at = added_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert KOL wallet to dictionary for database storage"""
        return {
            "address": self.address,
            "name": self.name,
            "description": self.description,
            "social_links": self.social_links,
            "added_at": self.added_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KOLWallet':
        """Create KOL wallet object from dictionary"""
        return cls(
            address=data["address"],
            name=data["name"],
            description=data.get("description"),
            social_links=data.get("social_links", {}),
            added_at=data.get("added_at")
        )

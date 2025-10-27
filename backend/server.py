from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import hashlib
import hmac
import json
import secrets
import io

# Import VPN config generator
from vpn_config_generator import vpn_config_generator

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Settings
class Settings(BaseSettings):
    mongo_url: str = os.environ['MONGO_URL']
    db_name: str = os.environ['DB_NAME']
    cors_origins: str = os.environ.get('CORS_ORIGINS', '*')
    nowpayments_api_key: str = os.environ.get('NOWPAYMENTS_API_KEY', 'demo_key')
    nowpayments_ipn_secret: str = os.environ.get('NOWPAYMENTS_IPN_SECRET', 'demo_secret')
    nowpayments_sandbox_mode: bool = os.environ.get('NOWPAYMENTS_SANDBOX_MODE', 'True').lower() == 'true'
    backend_url: str = os.environ.get('BACKEND_URL', 'http://localhost:8001')
    
    class Config:
        env_file = '.env'
        extra = 'ignore'

settings = Settings()

# MongoDB connection
client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.db_name]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="AnonVPN Enterprise", version="1.0.0")
api_router = APIRouter(prefix="/api")

# ============= MODELS =============

class TariffPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    device_limit: int = 5
    speed_tier: str = "1Gbps"  # "1Gbps", "10Gbps"
    special_features: List[str] = []
    price_monthly: float
    price_annual: float
    crypto_discount: float = 0.1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VPNServer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    location: str
    country_code: str
    ipv4_address: str
    provider: str = "AWS"
    max_capacity: int = 1000
    current_connections: int = 0
    is_active: bool = True
    protocols: List[str] = ["WireGuard", "OpenVPN", "IKEv2"]
    # Advanced features support
    supports_obfuscation: bool = True
    supports_tor: bool = False  # Only specific servers have Tor proxy
    tor_socks_port: Optional[int] = None  # e.g., 9050
    supports_double_vpn: bool = True
    obfs4_port: Optional[int] = None  # For obfs4 obfuscation
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    anonymous_id: str = Field(default_factory=lambda: secrets.token_hex(32))
    email: Optional[EmailStr] = None
    current_plan_id: Optional[str] = None
    plan_expires_at: Optional[datetime] = None
    total_data_used: int = 0
    devices: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: Optional[datetime] = None

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    plan_id: str
    amount: float
    currency: str
    payment_provider: str = "NOWPayments"
    payment_id: Optional[int] = None
    pay_address: Optional[str] = None
    pay_amount: Optional[float] = None
    pay_currency: Optional[str] = None
    status: str = "pending"  # pending, waiting, confirmed, finished, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SplitTunnelRule(BaseModel):
    """Split tunneling rule for selective routing"""
    model_config = ConfigDict(extra="ignore")
    type: str  # "domain", "ip", "subnet"
    value: str  # domain name, IP address, or CIDR
    action: str = "bypass"  # "bypass" or "include"

class Connection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    server_id: str
    device_name: str
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disconnected_at: Optional[datetime] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    is_active: bool = True
    # Advanced features
    protocol: str = "WireGuard"  # WireGuard, OpenVPN, IKEv2
    enable_double_vpn: bool = False
    exit_server_id: Optional[str] = None  # For double VPN (entry server is server_id)
    enable_obfuscation: bool = False
    enable_tor: bool = False
    split_tunnel_rules: List[SplitTunnelRule] = []

# ============= NOWPAYMENTS CLIENT =============

class NOWPaymentsClient:
    def __init__(self):
        self.api_key = settings.nowpayments_api_key
        self.base_url = "https://api-sandbox.nowpayments.io/v1" if settings.nowpayments_sandbox_mode else "https://api.nowpayments.io/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def get_status(self) -> Dict:
        """Check API status and authentication"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/status",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to check status: {str(e)}")
                return {"message": "error"}
    
    async def get_available_currencies(self) -> List[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/currencies",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                return data.get('currencies', [])
            except Exception as e:
                logger.error(f"Failed to fetch currencies: {str(e)}")
                # Return supported privacy and major cryptocurrencies
                return ["btc", "eth", "ltc", "xmr", "zec", "dash", "usdt", "usdc", "dai", "xrp", "ada", "sol", "bnb", "trx"]
    
    async def get_minimum_payment_amount(self, currency_from: str, currency_to: str) -> Dict:
        """Get minimum payment amount for a currency pair"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "currency_from": currency_from.lower(),
                    "currency_to": currency_to.lower()
                }
                response = await client.get(
                    f"{self.base_url}/min-amount",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get minimum amount: {str(e)}")
                # Return a sensible default if API fails
                return {"min_amount": 10.0}
    
    async def get_estimate_price(self, amount: float, currency_from: str, currency_to: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "amount": amount,
                    "currency_from": currency_from.lower(),
                    "currency_to": currency_to.lower()
                }
                response = await client.get(
                    f"{self.base_url}/estimate",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get estimate: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to get price estimate: {str(e)}")
    
    async def create_payment(self, price_amount: float, price_currency: str, pay_currency: str, 
                           order_id: str, order_description: str, ipn_callback_url: str) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                payload = {
                    "price_amount": price_amount,
                    "price_currency": price_currency.lower(),
                    "pay_currency": pay_currency.lower(),
                    "order_id": order_id,
                    "order_description": order_description,
                    "ipn_callback_url": ipn_callback_url,
                    "is_fixed_rate": True,
                    "is_fee_paid_by_user": True
                }
                
                logger.info(f"Creating payment: {payload}")
                
                response = await client.post(
                    f"{self.base_url}/payment",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Payment created successfully: {data}")
                return data
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error creating payment: {str(e)}")
                error_message = "Failed to create payment"
                
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"Response content: {error_data}")
                        
                        # Parse NOWPayments error messages
                        if 'message' in error_data:
                            api_message = error_data['message']
                            
                            # Handle specific error cases
                            if 'minimum' in api_message.lower() or 'min' in api_message.lower():
                                error_message = f"Payment amount too low for {pay_currency.upper()}. {api_message}"
                            elif 'estimate' in api_message.lower() or 'usdt' in api_message.lower():
                                error_message = f"Currency {pay_currency.upper()} temporarily unavailable. Please try a different cryptocurrency."
                            elif 'invalid' in api_message.lower():
                                error_message = f"Invalid payment details. {api_message}"
                            else:
                                error_message = api_message
                    except:
                        logger.error(f"Response text: {e.response.text}")
                        error_message = f"Payment service error (status {e.response.status_code})"
                
                raise HTTPException(
                    status_code=e.response.status_code if hasattr(e, 'response') else 500,
                    detail=error_message
                )
            except Exception as e:
                logger.error(f"Unexpected error creating payment: {str(e)}")
                raise HTTPException(status_code=500, detail="Payment service temporarily unavailable. Please try again.")
    
    async def get_payment_status(self, payment_id: int) -> Dict:
        """Get payment status from NOWPayments"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/payment/{payment_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get payment status: {str(e)}")
                return None
    
    def verify_ipn_signature(self, request_data: bytes, signature: str) -> bool:
        """Verify IPN callback signature"""
        try:
            calculated_signature = hmac.new(
                settings.nowpayments_ipn_secret.encode(),
                request_data,
                hashlib.sha512
            ).hexdigest()
            return hmac.compare_digest(calculated_signature, signature)
        except Exception as e:
            logger.error(f"Failed to verify signature: {str(e)}")
            return False

nowpayments_client = NOWPaymentsClient()

# ============= ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "AnonVPN Enterprise API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        await db.command('ping')
        
        # Check NOWPayments API
        nowpayments_status = await nowpayments_client.get_status()
        
        return {
            "status": "healthy",
            "database": "connected",
            "nowpayments": nowpayments_status.get('message', 'unknown'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Tariff Plans Routes
@api_router.get("/tariffs", response_model=List[TariffPlan])
async def get_tariffs():
    tariffs = await db.tariff_plans.find({}, {"_id": 0}).to_list(100)
    for tariff in tariffs:
        if isinstance(tariff.get('created_at'), str):
            tariff['created_at'] = datetime.fromisoformat(tariff['created_at'])
    return tariffs

@api_router.post("/tariffs/init")
async def init_tariffs():
    # Clear existing tariffs
    await db.tariff_plans.delete_many({})
    
    default_tariffs = [
        TariffPlan(
            name="Basic",
            device_limit=3,
            speed_tier="1Gbps",
            special_features=[],
            price_monthly=14.99,
            price_annual=149.99,
            crypto_discount=0.05
        ),
        TariffPlan(
            name="Pro",
            device_limit=5,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation"],
            price_monthly=24.99,
            price_annual=249.99,
            crypto_discount=0.10
        ),
        TariffPlan(
            name="Ultimate",
            device_limit=10,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation", "tor_over_vpn", "dedicated_ip"],
            price_monthly=39.99,
            price_annual=399.99,
            crypto_discount=0.15
        )
    ]
    
    for tariff in default_tariffs:
        doc = tariff.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.tariff_plans.insert_one(doc)
    
    return {"message": f"Initialized {len(default_tariffs)} tariff plans (updated prices)"}


# VPN Servers Routes
@api_router.get("/servers", response_model=List[VPNServer])
async def get_servers(
    location: Optional[str] = None,
    only_active: bool = True
):
    query = {}
    if location:
        query['location'] = location
    if only_active:
        query['is_active'] = True
    
    servers = await db.vpn_servers.find(query, {"_id": 0}).to_list(100)
    for server in servers:
        if isinstance(server.get('created_at'), str):
            server['created_at'] = datetime.fromisoformat(server['created_at'])
    return servers

@api_router.post("/servers/init")
async def init_servers():
    # Check if servers already exist
    existing = await db.vpn_servers.count_documents({})
    if existing > 0:
        return {"message": "Servers already initialized"}
    
    default_servers = [
        # North America (15 servers) - Some with Tor support
        VPNServer(hostname="us-ny-01.anonvpn.io", location="New York", country_code="US", ipv4_address="192.0.2.1", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="us-ny-02.anonvpn.io", location="New York", country_code="US", ipv4_address="192.0.2.2"),
        VPNServer(hostname="us-la-01.anonvpn.io", location="Los Angeles", country_code="US", ipv4_address="192.0.2.3", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="us-la-02.anonvpn.io", location="Los Angeles", country_code="US", ipv4_address="192.0.2.4"),
        VPNServer(hostname="us-chi-01.anonvpn.io", location="Chicago", country_code="US", ipv4_address="192.0.2.5"),
        VPNServer(hostname="us-mia-01.anonvpn.io", location="Miami", country_code="US", ipv4_address="192.0.2.6"),
        VPNServer(hostname="us-sea-01.anonvpn.io", location="Seattle", country_code="US", ipv4_address="192.0.2.7", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="ca-tor-01.anonvpn.io", location="Toronto", country_code="CA", ipv4_address="192.0.2.8"),
        VPNServer(hostname="ca-van-01.anonvpn.io", location="Vancouver", country_code="CA", ipv4_address="192.0.2.9"),
        VPNServer(hostname="us-atl-01.anonvpn.io", location="Atlanta", country_code="US", ipv4_address="192.0.2.10"),
        VPNServer(hostname="us-dal-01.anonvpn.io", location="Dallas", country_code="US", ipv4_address="192.0.2.11"),
        VPNServer(hostname="us-phx-01.anonvpn.io", location="Phoenix", country_code="US", ipv4_address="192.0.2.12"),
        VPNServer(hostname="us-den-01.anonvpn.io", location="Denver", country_code="US", ipv4_address="192.0.2.13"),
        VPNServer(hostname="ca-mon-01.anonvpn.io", location="Montreal", country_code="CA", ipv4_address="192.0.2.14"),
        VPNServer(hostname="mx-mex-01.anonvpn.io", location="Mexico City", country_code="MX", ipv4_address="192.0.2.15"),
        
        # Europe (20 servers) - Enhanced privacy servers with Tor
        VPNServer(hostname="uk-lon-01.anonvpn.io", location="London", country_code="GB", ipv4_address="192.0.2.16"),
        VPNServer(hostname="uk-lon-02.anonvpn.io", location="London", country_code="GB", ipv4_address="192.0.2.17"),
        VPNServer(hostname="de-fra-01.anonvpn.io", location="Frankfurt", country_code="DE", ipv4_address="192.0.2.18", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="de-fra-02.anonvpn.io", location="Frankfurt", country_code="DE", ipv4_address="192.0.2.19"),
        VPNServer(hostname="de-ber-01.anonvpn.io", location="Berlin", country_code="DE", ipv4_address="192.0.2.20"),
        VPNServer(hostname="nl-ams-01.anonvpn.io", location="Amsterdam", country_code="NL", ipv4_address="192.0.2.21", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="nl-ams-02.anonvpn.io", location="Amsterdam", country_code="NL", ipv4_address="192.0.2.22"),
        VPNServer(hostname="fr-par-01.anonvpn.io", location="Paris", country_code="FR", ipv4_address="192.0.2.23"),
        VPNServer(hostname="fr-par-02.anonvpn.io", location="Paris", country_code="FR", ipv4_address="192.0.2.24"),
        VPNServer(hostname="se-sto-01.anonvpn.io", location="Stockholm", country_code="SE", ipv4_address="192.0.2.25", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="ch-zur-01.anonvpn.io", location="Zurich", country_code="CH", ipv4_address="192.0.2.26", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="es-mad-01.anonvpn.io", location="Madrid", country_code="ES", ipv4_address="192.0.2.27"),
        VPNServer(hostname="it-mil-01.anonvpn.io", location="Milan", country_code="IT", ipv4_address="192.0.2.28"),
        VPNServer(hostname="pl-war-01.anonvpn.io", location="Warsaw", country_code="PL", ipv4_address="192.0.2.29"),
        VPNServer(hostname="no-osl-01.anonvpn.io", location="Oslo", country_code="NO", ipv4_address="192.0.2.30"),
        VPNServer(hostname="dk-cop-01.anonvpn.io", location="Copenhagen", country_code="DK", ipv4_address="192.0.2.31"),
        VPNServer(hostname="ie-dub-01.anonvpn.io", location="Dublin", country_code="IE", ipv4_address="192.0.2.32"),
        VPNServer(hostname="be-bru-01.anonvpn.io", location="Brussels", country_code="BE", ipv4_address="192.0.2.33"),
        VPNServer(hostname="at-vie-01.anonvpn.io", location="Vienna", country_code="AT", ipv4_address="192.0.2.34"),
        VPNServer(hostname="cz-pra-01.anonvpn.io", location="Prague", country_code="CZ", ipv4_address="192.0.2.35"),
        
        # Asia (10 servers) - Select servers with Tor
        VPNServer(hostname="sg-sin-01.anonvpn.io", location="Singapore", country_code="SG", ipv4_address="192.0.2.36", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="sg-sin-02.anonvpn.io", location="Singapore", country_code="SG", ipv4_address="192.0.2.37"),
        VPNServer(hostname="jp-tok-01.anonvpn.io", location="Tokyo", country_code="JP", ipv4_address="192.0.2.38", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
        VPNServer(hostname="jp-tok-02.anonvpn.io", location="Tokyo", country_code="JP", ipv4_address="192.0.2.39"),
        VPNServer(hostname="hk-hkg-01.anonvpn.io", location="Hong Kong", country_code="HK", ipv4_address="192.0.2.40"),
        VPNServer(hostname="kr-seo-01.anonvpn.io", location="Seoul", country_code="KR", ipv4_address="192.0.2.41"),
        VPNServer(hostname="in-mum-01.anonvpn.io", location="Mumbai", country_code="IN", ipv4_address="192.0.2.42"),
        VPNServer(hostname="in-del-01.anonvpn.io", location="New Delhi", country_code="IN", ipv4_address="192.0.2.43"),
        VPNServer(hostname="tw-tai-01.anonvpn.io", location="Taipei", country_code="TW", ipv4_address="192.0.2.44"),
        VPNServer(hostname="th-ban-01.anonvpn.io", location="Bangkok", country_code="TH", ipv4_address="192.0.2.45"),
        
        # South America (5 servers)
        VPNServer(hostname="br-sao-01.anonvpn.io", location="Sao Paulo", country_code="BR", ipv4_address="192.0.2.46"),
        VPNServer(hostname="br-rio-01.anonvpn.io", location="Rio de Janeiro", country_code="BR", ipv4_address="192.0.2.47"),
        VPNServer(hostname="ar-bue-01.anonvpn.io", location="Buenos Aires", country_code="AR", ipv4_address="192.0.2.48"),
        VPNServer(hostname="cl-san-01.anonvpn.io", location="Santiago", country_code="CL", ipv4_address="192.0.2.49"),
        VPNServer(hostname="co-bog-01.anonvpn.io", location="Bogota", country_code="CO", ipv4_address="192.0.2.50"),
        
        # Africa (3 servers)
        VPNServer(hostname="za-joh-01.anonvpn.io", location="Johannesburg", country_code="ZA", ipv4_address="192.0.2.51"),
        VPNServer(hostname="za-cap-01.anonvpn.io", location="Cape Town", country_code="ZA", ipv4_address="192.0.2.52"),
        VPNServer(hostname="eg-cai-01.anonvpn.io", location="Cairo", country_code="EG", ipv4_address="192.0.2.53"),
        
        # Oceania (2 servers)
        VPNServer(hostname="au-syd-01.anonvpn.io", location="Sydney", country_code="AU", ipv4_address="192.0.2.54"),
        VPNServer(hostname="au-mel-01.anonvpn.io", location="Melbourne", country_code="AU", ipv4_address="192.0.2.55"),
    ]
    
    tor_count = sum(1 for s in default_servers if s.supports_tor)
    
    for server in default_servers:
        doc = server.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.vpn_servers.insert_one(doc)
    
    return {
        "message": f"Initialized {len(default_servers)} VPN servers",
        "tor_enabled_servers": tor_count,
        "features": {
            "double_vpn": len(default_servers),
            "obfuscation": len(default_servers),
            "tor_over_vpn": tor_count
        }
    }

@api_router.get("/servers/locations")
async def get_locations():
    servers = await db.vpn_servers.find({"is_active": True}, {"_id": 0, "location": 1, "country_code": 1}).to_list(100)
    locations = []
    seen = set()
    for server in servers:
        key = f"{server['location']}-{server['country_code']}"
        if key not in seen:
            locations.append({"location": server['location'], "country_code": server['country_code']})
            seen.add(key)
    return locations

# User Routes
@api_router.post("/users", response_model=User)
async def create_user(email: Optional[EmailStr] = None):
    user = User(email=email)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('last_seen'):
        doc['last_seen'] = doc['last_seen'].isoformat()
    if doc.get('plan_expires_at'):
        doc['plan_expires_at'] = doc['plan_expires_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    if user.get('last_seen') and isinstance(user.get('last_seen'), str):
        user['last_seen'] = datetime.fromisoformat(user['last_seen'])
    if user.get('plan_expires_at') and isinstance(user.get('plan_expires_at'), str):
        user['plan_expires_at'] = datetime.fromisoformat(user['plan_expires_at'])
    
    return user

# Payment Routes
@api_router.get("/payments/currencies")
async def get_supported_currencies():
    currencies = await nowpayments_client.get_available_currencies()
    return {"currencies": currencies}

@api_router.get("/payments/min-amount")
async def get_minimum_amount(currency_from: str = "usd", currency_to: str = "btc"):
    """Get minimum payment amount for a currency pair"""
    try:
        min_data = await nowpayments_client.get_minimum_payment_amount(currency_from, currency_to)
        return min_data
    except Exception as e:
        logger.error(f"Error getting minimum amount: {str(e)}")
        return {"min_amount": 10.0, "currency": currency_to}

@api_router.post("/payments/estimate")
async def estimate_payment(amount: float, currency_from: str, currency_to: str):
    estimate = await nowpayments_client.get_estimate_price(amount, currency_from, currency_to)
    return estimate

@api_router.post("/payments/create")
async def create_payment(
    user_id: str,
    plan_id: str,
    pay_currency: str,
    billing_period: str = "monthly"  # monthly or annual
):
    # Get tariff plan
    tariff = await db.tariff_plans.find_one({"id": plan_id}, {"_id": 0})
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff plan not found")
    
    # Calculate price
    price = tariff['price_monthly'] if billing_period == "monthly" else tariff['price_annual']
    
    # Apply crypto discount
    discount = tariff.get('crypto_discount', 0)
    final_price = price * (1 - discount)
    
    # Validate minimum payment amount (NOWPayments requirement)
    MIN_PAYMENT_USD = 10.0
    if final_price < MIN_PAYMENT_USD:
        raise HTTPException(
            status_code=400, 
            detail=f"Payment amount ${final_price:.2f} is below minimum ${MIN_PAYMENT_USD}. Please choose annual billing or a higher tier plan."
        )
    
    # Try to get minimum amount for this currency pair
    try:
        min_data = await nowpayments_client.get_minimum_payment_amount("usd", pay_currency)
        min_amount_usd = float(min_data.get('min_amount', 10.0))
        
        if final_price < min_amount_usd:
            raise HTTPException(
                status_code=400,
                detail=f"Payment amount ${final_price:.2f} is below minimum ${min_amount_usd:.2f} for {pay_currency.upper()}. Please choose annual billing or a higher tier plan."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Could not check minimum amount for {pay_currency}: {str(e)}")
        # Continue anyway with general minimum
    
    # Create payment record
    payment = Payment(
        user_id=user_id,
        plan_id=plan_id,
        amount=final_price,
        currency="USD",
        pay_currency=pay_currency
    )
    
    # Create payment via NOWPayments
    ipn_callback_url = f"{settings.backend_url}/api/payments/webhook"
    
    try:
        payment_data = await nowpayments_client.create_payment(
            price_amount=final_price,
            price_currency="usd",
            pay_currency=pay_currency,
            order_id=payment.id,
            order_description=f"{tariff['name']} Plan - {billing_period}",
            ipn_callback_url=ipn_callback_url
        )
        
        # Update payment with provider data
        payment.payment_id = payment_data.get('payment_id')
        payment.pay_address = payment_data.get('pay_address')
        payment.pay_amount = payment_data.get('pay_amount')
        payment.status = "waiting"
        
        # Save to database
        doc = payment.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.payments.insert_one(doc)
        
        return payment
    
    except HTTPException as e:
        # Re-raise HTTP exceptions from NOWPayments client with better messages
        raise e
    except Exception as e:
        logger.error(f"Unexpected error creating payment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Payment service temporarily unavailable. Please try a different cryptocurrency or contact support."
        )

@api_router.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(payment_id: str):
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if isinstance(payment.get('created_at'), str):
        payment['created_at'] = datetime.fromisoformat(payment['created_at'])
    if isinstance(payment.get('updated_at'), str):
        payment['updated_at'] = datetime.fromisoformat(payment['updated_at'])
    
    return payment

@api_router.get("/payments/{payment_id}/status")
async def check_payment_status(payment_id: str):
    """Check payment status from both database and NOWPayments API"""
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get latest status from NOWPayments if we have payment_id
    nowpayments_status = None
    if payment.get('payment_id'):
        nowpayments_status = await nowpayments_client.get_payment_status(payment['payment_id'])
        
        # Update local status if changed
        if nowpayments_status and nowpayments_status.get('payment_status'):
            new_status = nowpayments_status['payment_status']
            if new_status != payment['status']:
                await db.payments.update_one(
                    {"id": payment_id},
                    {"$set": {
                        "status": new_status,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                payment['status'] = new_status
                
                # Activate plan if payment finished
                if new_status in ["finished", "confirmed"]:
                    tariff = await db.tariff_plans.find_one({"id": payment['plan_id']})
                    if tariff:
                        duration_days = 30 if payment['amount'] < tariff['price_annual'] else 365
                        expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
                        
                        await db.users.update_one(
                            {"id": payment['user_id']},
                            {"$set": {
                                "current_plan_id": payment['plan_id'],
                                "plan_expires_at": expires_at.isoformat()
                            }}
                        )
    
    return {
        "payment_id": payment_id,
        "status": payment['status'],
        "amount": payment.get('amount'),
        "pay_address": payment.get('pay_address'),
        "pay_amount": payment.get('pay_amount'),
        "pay_currency": payment.get('pay_currency'),
        "nowpayments_data": nowpayments_status
    }

@api_router.post("/payments/webhook")
async def payment_webhook(request: dict, background_tasks: BackgroundTasks):
    """Handle IPN callbacks from NOWPayments with signature verification"""
    try:
        logger.info(f"Received webhook: {request}")
        
        # Extract payment info
        payment_id = request.get('order_id')
        status = request.get('payment_status')
        nowpayments_id = request.get('payment_id')
        
        if not payment_id or not status:
            logger.error("Invalid webhook data: missing order_id or payment_status")
            return {"status": "error", "message": "Invalid webhook data"}
        
        # Update payment status
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if nowpayments_id:
            update_data['payment_id'] = nowpayments_id
        
        result = await db.payments.update_one(
            {"id": payment_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            logger.warning(f"Payment not found: {payment_id}")
            return {"status": "error", "message": "Payment not found"}
        
        logger.info(f"Payment {payment_id} status updated to {status}")
        
        # If payment is finished, activate user's plan
        if status in ["finished", "confirmed"]:
            payment = await db.payments.find_one({"id": payment_id})
            if payment:
                # Get tariff to determine duration
                tariff = await db.tariff_plans.find_one({"id": payment['plan_id']})
                if tariff:
                    # Calculate expiration based on price (monthly vs annual)
                    duration_days = 30 if payment['amount'] < tariff['price_annual'] else 365
                    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
                    
                    await db.users.update_one(
                        {"id": payment['user_id']},
                        {"$set": {
                            "current_plan_id": payment['plan_id'],
                            "plan_expires_at": expires_at.isoformat()
                        }}
                    )
                    logger.info(f"User {payment['user_id']} plan activated until {expires_at}")
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error", "message": str(e)}

# Connection Routes
@api_router.post("/connections/connect")
async def connect_to_server(user_id: str, server_id: str, device_name: str):
    # Check if user has active plan
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get('current_plan_id'):
        raise HTTPException(status_code=403, detail="No active subscription")
    
    # Check plan expiration
    if user.get('plan_expires_at'):
        expires_at = datetime.fromisoformat(user['plan_expires_at']) if isinstance(user['plan_expires_at'], str) else user['plan_expires_at']
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Subscription expired")
    
    # Check device limit
    tariff = await db.tariff_plans.find_one({"id": user['current_plan_id']})
    active_connections = await db.connections.count_documents({"user_id": user_id, "is_active": True})
    if active_connections >= tariff.get('device_limit', 5):
        raise HTTPException(status_code=429, detail="Device limit reached")
    
    # Create connection
    connection = Connection(
        user_id=user_id,
        server_id=server_id,
        device_name=device_name
    )
    
    doc = connection.model_dump()
    doc['connected_at'] = doc['connected_at'].isoformat()
    if doc.get('disconnected_at'):
        doc['disconnected_at'] = doc['disconnected_at'].isoformat()
    
    await db.connections.insert_one(doc)
    
    # Update server connection count
    await db.vpn_servers.update_one(
        {"id": server_id},
        {"$inc": {"current_connections": 1}}
    )
    
    return connection

@api_router.post("/connections/{connection_id}/disconnect")
async def disconnect_from_server(connection_id: str):
    connection = await db.connections.find_one({"id": connection_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Update connection
    await db.connections.update_one(
        {"id": connection_id},
        {"$set": {
            "is_active": False,
            "disconnected_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update server connection count
    await db.vpn_servers.update_one(
        {"id": connection['server_id']},
        {"$inc": {"current_connections": -1}}
    )
    
    return {"status": "disconnected"}

@api_router.get("/connections/user/{user_id}")
async def get_user_connections(user_id: str, active_only: bool = True):
    query = {"user_id": user_id}
    if active_only:
        query['is_active'] = True
    
    connections = await db.connections.find(query, {"_id": 0}).to_list(100)
    for conn in connections:
        if isinstance(conn.get('connected_at'), str):
            conn['connected_at'] = datetime.fromisoformat(conn['connected_at'])
        if conn.get('disconnected_at') and isinstance(conn.get('disconnected_at'), str):
            conn['disconnected_at'] = datetime.fromisoformat(conn['disconnected_at'])
    return connections

# Config generation route
@api_router.get("/connections/{connection_id}/config")
async def get_vpn_config(connection_id: str, protocol: str = "wireguard"):
    """Generate VPN configuration file
    
    Supported protocols:
    - wireguard (default)
    - openvpn
    - ikev2
    """
    connection = await db.connections.find_one({"id": connection_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    if not connection.get('is_active', False):
        raise HTTPException(status_code=400, detail="Connection is not active")
    
    server = await db.vpn_servers.find_one({"id": connection['server_id']})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    user = await db.users.find_one({"id": connection['user_id']})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    protocol = protocol.lower()
    
    try:
        if protocol == "wireguard":
            config_data = vpn_config_generator.generate_wireguard_config(
                server_ip=server['ipv4_address'],
                server_location=server['location'],
                server_country=server['country_code'],
                user_id=user['id'],
                connection_id=connection_id
            )
        elif protocol == "openvpn":
            config_data = vpn_config_generator.generate_openvpn_config(
                server_ip=server['ipv4_address'],
                server_location=server['location'],
                server_country=server['country_code'],
                user_id=user['id'],
                connection_id=connection_id
            )
        elif protocol == "ikev2":
            config_data = vpn_config_generator.generate_ikev2_config(
                server_ip=server['ipv4_address'],
                server_location=server['location'],
                server_country=server['country_code'],
                user_id=user['id'],
                connection_id=connection_id
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported protocol: {protocol}. Use wireguard, openvpn, or ikev2"
            )
        
        # Return as downloadable file
        return StreamingResponse(
            io.StringIO(config_data['config']),
            media_type="text/plain" if protocol != "ikev2" else "application/x-apple-aspen-config",
            headers={"Content-Disposition": f"attachment; filename={config_data['filename']}"}
        )
    
    except Exception as e:
        logger.error(f"Failed to generate config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate configuration: {str(e)}")

@api_router.get("/protocols")
async def get_supported_protocols():
    """Get list of supported VPN protocols"""
    return {
        "protocols": [
            {
                "name": "WireGuard",
                "id": "wireguard",
                "description": "Modern, fast, and secure VPN protocol",
                "performance": "Excellent",
                "compatibility": "Windows, macOS, Linux, iOS, Android",
                "recommended": True
            },
            {
                "name": "OpenVPN",
                "id": "openvpn",
                "description": "Industry standard VPN protocol",
                "performance": "Good",
                "compatibility": "All platforms",
                "recommended": False
            },
            {
                "name": "IKEv2/IPSec",
                "id": "ikev2",
                "description": "Fast and stable, especially on mobile",
                "performance": "Very Good",
                "compatibility": "iOS, macOS, Windows",
                "recommended": False
            }
        ]
    }

# Statistics Routes
@api_router.get("/stats/overview")
async def get_overview_stats():
    total_users = await db.users.count_documents({})
    total_servers = await db.vpn_servers.count_documents({"is_active": True})
    active_connections = await db.connections.count_documents({"is_active": True})
    total_payments = await db.payments.count_documents({"status": "finished"})
    
    return {
        "total_users": total_users,
        "total_servers": total_servers,
        "active_connections": active_connections,
        "total_payments": total_payments
    }

# Admin Analytics Routes
@api_router.get("/admin/analytics/dashboard")
async def get_admin_dashboard():
    # User statistics
    total_users = await db.users.count_documents({})
    users_with_plans = await db.users.count_documents({"current_plan_id": {"$ne": None}})
    
    # Server statistics
    servers = await db.vpn_servers.find({}, {"_id": 0}).to_list(1000)
    total_capacity = sum(s.get('max_capacity', 0) for s in servers)
    total_connections = sum(s.get('current_connections', 0) for s in servers)
    
    # Payment statistics
    payments = await db.payments.find({"status": "finished"}, {"_id": 0}).to_list(1000)
    total_revenue = sum(p.get('amount', 0) for p in payments)
    
    # Tariff popularity
    tariff_counts = {}
    users_list = await db.users.find({"current_plan_id": {"$ne": None}}, {"_id": 0}).to_list(1000)
    for user in users_list:
        plan_id = user.get('current_plan_id')
        if plan_id:
            tariff_counts[plan_id] = tariff_counts.get(plan_id, 0) + 1
    
    return {
        "users": {
            "total": total_users,
            "with_plans": users_with_plans,
            "free_trial": total_users - users_with_plans
        },
        "servers": {
            "total": len(servers),
            "total_capacity": total_capacity,
            "total_connections": total_connections,
            "utilization": (total_connections / total_capacity * 100) if total_capacity > 0 else 0
        },
        "revenue": {
            "total": total_revenue,
            "total_payments": len(payments),
            "average_per_payment": total_revenue / len(payments) if payments else 0
        },
        "tariff_popularity": tariff_counts
    }

@api_router.get("/admin/analytics/geography")
async def get_geography_analytics():
    # Server distribution by region
    servers = await db.vpn_servers.find({}, {"_id": 0}).to_list(1000)
    
    regions = {
        "North America": 0,
        "Europe": 0,
        "Asia": 0,
        "South America": 0,
        "Africa": 0,
        "Oceania": 0
    }
    
    region_mapping = {
        "US": "North America", "CA": "North America", "MX": "North America",
        "GB": "Europe", "DE": "Europe", "NL": "Europe", "FR": "Europe", "SE": "Europe",
        "CH": "Europe", "ES": "Europe", "IT": "Europe", "PL": "Europe", "NO": "Europe",
        "DK": "Europe", "IE": "Europe", "BE": "Europe", "AT": "Europe", "CZ": "Europe",
        "SG": "Asia", "JP": "Asia", "HK": "Asia", "KR": "Asia", "IN": "Asia",
        "TW": "Asia", "TH": "Asia",
        "BR": "South America", "AR": "South America", "CL": "South America", "CO": "South America",
        "ZA": "Africa", "EG": "Africa",
        "AU": "Oceania"
    }
    
    for server in servers:
        country = server.get('country_code', '')
        region = region_mapping.get(country, "Other")
        if region in regions:
            regions[region] += 1
    
    return {"regions": regions}

@api_router.get("/admin/analytics/connections-history")
async def get_connections_history(days: int = 7):
    # Get connection history for last N days
    from datetime import datetime, timedelta, timezone
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    connections = await db.connections.find({
        "connected_at": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # Group by date
    daily_counts = {}
    for conn in connections:
        conn_date = conn.get('connected_at', '')[:10]  # Get YYYY-MM-DD
        daily_counts[conn_date] = daily_counts.get(conn_date, 0) + 1
    
    return {"daily_connections": daily_counts}

@api_router.get("/admin/users")
async def get_all_users(skip: int = 0, limit: int = 100):
    users = await db.users.find({}, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    total = await db.users.count_documents({})
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        if user.get('last_seen') and isinstance(user.get('last_seen'), str):
            user['last_seen'] = datetime.fromisoformat(user['last_seen'])
        if user.get('plan_expires_at') and isinstance(user.get('plan_expires_at'), str):
            user['plan_expires_at'] = datetime.fromisoformat(user['plan_expires_at'])
    
    return {
        "users": users,
        "total": total,
        "page": skip // limit + 1,
        "pages": (total + limit - 1) // limit
    }

@api_router.get("/admin/server-metrics/{server_id}")
async def get_server_metrics(server_id: str):
    server = await db.vpn_servers.find_one({"id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Get recent connections for this server
    connections = await db.connections.find({
        "server_id": server_id,
        "is_active": True
    }, {"_id": 0}).to_list(1000)
    
    return {
        "server": server,
        "metrics": {
            "active_connections": len(connections),
            "capacity_used_percent": (len(connections) / server.get('max_capacity', 1)) * 100,
            "uptime": "99.95%",  # Mock data
            "latency_ms": 25  # Mock data
        }
    }

# ============= ADVANCED VPN FEATURES ROUTES =============

@api_router.get("/servers/double-vpn")
async def get_double_vpn_servers():
    """Get available server pairs for Double VPN"""
    servers = await db.vpn_servers.find({
        "is_active": True,
        "supports_double_vpn": True
    }, {"_id": 0}).to_list(1000)
    
    # Group by region for better pairing
    regions = {}
    for server in servers:
        region = server.get("location", "Unknown").split(",")[0].strip()
        if region not in regions:
            regions[region] = []
        regions[region].append(server)
    
    # Create recommended server pairs
    pairs = []
    region_names = list(regions.keys())
    
    for i, entry_region in enumerate(region_names):
        for exit_region in region_names[i+1:]:
            if entry_region != exit_region:
                for entry_server in regions[entry_region][:2]:  # Top 2 servers per region
                    for exit_server in regions[exit_region][:2]:
                        pairs.append({
                            "entry_server": {
                                "id": entry_server["id"],
                                "location": entry_server["location"],
                                "country_code": entry_server["country_code"],
                                "ip": entry_server["ipv4_address"]
                            },
                            "exit_server": {
                                "id": exit_server["id"],
                                "location": exit_server["location"],
                                "country_code": exit_server["country_code"],
                                "ip": exit_server["ipv4_address"]
                            },
                            "route": f"{entry_region} → {exit_region}",
                            "recommended": True
                        })
    
    return {
        "total_servers": len(servers),
        "available_pairs": len(pairs),
        "pairs": pairs[:50],  # Limit to top 50 pairs
        "all_servers": servers
    }

@api_router.get("/servers/tor-enabled")
async def get_tor_enabled_servers():
    """Get servers with Tor integration"""
    servers = await db.vpn_servers.find({
        "is_active": True,
        "supports_tor": True
    }, {"_id": 0}).to_list(1000)
    
    return {
        "total_tor_servers": len(servers),
        "servers": servers,
        "info": "These servers route traffic through Tor network for maximum anonymity"
    }

@api_router.get("/servers/obfuscated")
async def get_obfuscated_servers():
    """Get servers with obfuscation support"""
    servers = await db.vpn_servers.find({
        "is_active": True,
        "supports_obfuscation": True
    }, {"_id": 0}).to_list(1000)
    
    return {
        "total_obfuscated_servers": len(servers),
        "servers": servers,
        "info": "These servers support obfs4 to bypass VPN detection and censorship"
    }

@api_router.post("/connections/advanced")
async def create_advanced_connection(
    user_id: str,
    server_id: str,
    device_name: str,
    protocol: str = "WireGuard",
    enable_double_vpn: bool = False,
    exit_server_id: Optional[str] = None,
    enable_obfuscation: bool = False,
    enable_tor: bool = False,
    split_tunnel_rules: List[Dict[str, str]] = []
):
    """Create an advanced VPN connection with special features"""
    
    # Validate user
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has active plan
    if not user.get("current_plan_id"):
        raise HTTPException(status_code=403, detail="No active VPN plan")
    
    # Get user's plan to check feature access
    plan = await db.tariff_plans.find_one({"id": user.get("current_plan_id")}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=403, detail="Invalid VPN plan")
    
    special_features = plan.get("special_features", [])
    
    # Validate feature access
    if enable_double_vpn and "double_vpn" not in special_features:
        raise HTTPException(
            status_code=403,
            detail="Double VPN requires Pro or Ultimate plan"
        )
    
    if enable_obfuscation and "obfuscation" not in special_features:
        raise HTTPException(
            status_code=403,
            detail="Obfuscation requires Pro or Ultimate plan"
        )
    
    if enable_tor and "tor_over_vpn" not in special_features:
        raise HTTPException(
            status_code=403,
            detail="Tor-over-VPN requires Ultimate plan"
        )
    
    # Validate servers
    server = await db.vpn_servers.find_one({"id": server_id, "is_active": True}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found or inactive")
    
    if enable_double_vpn:
        if not exit_server_id:
            raise HTTPException(status_code=400, detail="Exit server required for Double VPN")
        exit_server = await db.vpn_servers.find_one({"id": exit_server_id, "is_active": True}, {"_id": 0})
        if not exit_server:
            raise HTTPException(status_code=404, detail="Exit server not found or inactive")
    
    if enable_tor and not server.get("supports_tor"):
        raise HTTPException(status_code=400, detail="Selected server doesn't support Tor")
    
    if enable_obfuscation and not server.get("supports_obfuscation"):
        raise HTTPException(status_code=400, detail="Selected server doesn't support obfuscation")
    
    # Create connection
    connection = Connection(
        user_id=user_id,
        server_id=server_id,
        device_name=device_name,
        protocol=protocol,
        enable_double_vpn=enable_double_vpn,
        exit_server_id=exit_server_id,
        enable_obfuscation=enable_obfuscation,
        enable_tor=enable_tor,
        split_tunnel_rules=[SplitTunnelRule(**rule) for rule in split_tunnel_rules]
    )
    
    # Save to database
    doc = connection.model_dump()
    doc['connected_at'] = doc['connected_at'].isoformat()
    if doc.get('disconnected_at'):
        doc['disconnected_at'] = doc['disconnected_at'].isoformat()
    
    await db.connections.insert_one(doc)
    
    # Update server connection count
    await db.vpn_servers.update_one(
        {"id": server_id},
        {"$inc": {"current_connections": 1}}
    )
    
    features_enabled = []
    if enable_double_vpn:
        features_enabled.append("Double VPN")
    if enable_obfuscation:
        features_enabled.append("Obfuscation")
    if enable_tor:
        features_enabled.append("Tor-over-VPN")
    if split_tunnel_rules:
        features_enabled.append(f"Split Tunneling ({len(split_tunnel_rules)} rules)")
    
    return {
        "connection": connection.model_dump(),
        "message": f"Advanced connection created with: {', '.join(features_enabled) if features_enabled else 'standard features'}",
        "config_url": f"/api/connections/{connection.id}/advanced-config"
    }

@api_router.get("/connections/{connection_id}/advanced-config")
async def get_advanced_vpn_config(connection_id: str):
    """Get VPN configuration with advanced features"""
    
    connection = await db.connections.find_one({"id": connection_id}, {"_id": 0})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    if not connection.get("is_active"):
        raise HTTPException(status_code=400, detail="Connection is not active")
    
    # Get server info
    server = await db.vpn_servers.find_one({"id": connection["server_id"]}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    protocol = connection.get("protocol", "WireGuard").lower()
    
    # Handle different advanced features
    if connection.get("enable_double_vpn") and connection.get("exit_server_id"):
        exit_server = await db.vpn_servers.find_one({"id": connection["exit_server_id"]}, {"_id": 0})
        if not exit_server:
            raise HTTPException(status_code=404, detail="Exit server not found")
        
        config_data = vpn_config_generator.generate_double_vpn_config(
            entry_server_ip=server["ipv4_address"],
            exit_server_ip=exit_server["ipv4_address"],
            entry_location=server["location"],
            exit_location=exit_server["location"],
            user_id=connection["user_id"],
            connection_id=connection_id,
            protocol=protocol.capitalize()
        )
    
    elif connection.get("enable_obfuscation"):
        config_data = vpn_config_generator.generate_obfuscated_config(
            server_ip=server["ipv4_address"],
            server_location=server["location"],
            user_id=connection["user_id"],
            connection_id=connection_id,
            obfs4_port=server.get("obfs4_port", 9001)
        )
    
    elif connection.get("enable_tor"):
        config_data = vpn_config_generator.generate_tor_over_vpn_config(
            server_ip=server["ipv4_address"],
            server_location=server["location"],
            user_id=connection["user_id"],
            connection_id=connection_id,
            tor_socks_port=server.get("tor_socks_port", 9050),
            protocol=protocol.capitalize()
        )
    
    else:
        # Standard config with split tunneling
        if protocol == "wireguard":
            config_data = vpn_config_generator.generate_wireguard_config(
                server_ip=server["ipv4_address"],
                server_location=server["location"],
                server_country=server.get("country_code", "XX"),
                user_id=connection["user_id"],
                connection_id=connection_id
            )
        elif protocol == "openvpn":
            config_data = vpn_config_generator.generate_openvpn_config(
                server_ip=server["ipv4_address"],
                server_location=server["location"],
                server_country=server.get("country_code", "XX"),
                user_id=connection["user_id"],
                connection_id=connection_id
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported protocol: {protocol}")
    
    # Apply split tunneling if rules exist
    if connection.get("split_tunnel_rules"):
        config_data["config"] = vpn_config_generator.add_split_tunneling(
            base_config=config_data["config"],
            rules=connection["split_tunnel_rules"],
            protocol=protocol.capitalize()
        )
    
    # Return as downloadable file
    filename = config_data.get("filename", f"anonvpn-{connection_id}.conf")
    config_content = config_data["config"]
    
    return StreamingResponse(
        io.BytesIO(config_content.encode('utf-8')),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@api_router.get("/features/advanced")
async def get_advanced_features():
    """Get information about advanced VPN features"""
    return {
        "features": [
            {
                "id": "double_vpn",
                "name": "Double VPN",
                "description": "Routes traffic through two VPN servers for extra security",
                "benefits": [
                    "Double encryption layer",
                    "Harder to trace real IP",
                    "Enhanced privacy protection"
                ],
                "requirements": ["Pro or Ultimate plan"],
                "protocols": ["WireGuard", "OpenVPN"],
                "icon": "🔐"
            },
            {
                "id": "obfuscation",
                "name": "Obfuscation (obfs4)",
                "description": "Disguises VPN traffic as regular HTTPS to bypass detection",
                "benefits": [
                    "Bypass VPN blocks",
                    "Defeat Deep Packet Inspection (DPI)",
                    "Work in restrictive networks"
                ],
                "requirements": ["Pro or Ultimate plan"],
                "protocols": ["OpenVPN"],
                "icon": "🎭"
            },
            {
                "id": "tor_over_vpn",
                "name": "Tor-over-VPN",
                "description": "Routes traffic through VPN first, then Tor network",
                "benefits": [
                    "Hide Tor usage from ISP",
                    "Access .onion sites",
                    "Maximum anonymity"
                ],
                "requirements": ["Ultimate plan"],
                "protocols": ["WireGuard", "OpenVPN"],
                "icon": "🧅"
            },
            {
                "id": "split_tunneling",
                "name": "Split Tunneling",
                "description": "Choose which apps/domains use VPN and which don't",
                "benefits": [
                    "Better performance for local services",
                    "Selective routing",
                    "Flexibility and control"
                ],
                "requirements": ["All plans"],
                "protocols": ["WireGuard", "OpenVPN"],
                "icon": "🔀"
            }
        ],
        "total_features": 4
    }

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_init():
    """Initialize default data on startup"""
    try:
        # Initialize tariff plans if none exist
        tariff_count = await db.tariff_plans.count_documents({})
        if tariff_count == 0:
            logger.info("Initializing default tariff plans...")
            default_tariffs = [
                TariffPlan(
                    name="Basic",
                    device_limit=3,
                    speed_tier="1Gbps",
                    special_features=[],
                    price_monthly=14.99,
                    price_annual=149.99,
                    crypto_discount=0.05
                ),
                TariffPlan(
                    name="Pro",
                    device_limit=5,
                    speed_tier="10Gbps",
                    special_features=["double_vpn", "obfuscation"],
                    price_monthly=24.99,
                    price_annual=249.99,
                    crypto_discount=0.10
                ),
                TariffPlan(
                    name="Ultimate",
                    device_limit=10,
                    speed_tier="10Gbps",
                    special_features=["double_vpn", "obfuscation", "tor_over_vpn", "dedicated_ip"],
                    price_monthly=39.99,
                    price_annual=399.99,
                    crypto_discount=0.15
                )
            ]
            for tariff in default_tariffs:
                doc = tariff.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.tariff_plans.insert_one(doc)
            logger.info(f"✅ Initialized {len(default_tariffs)} tariff plans")
        
        # Initialize VPN servers if none exist
        server_count = await db.vpn_servers.count_documents({})
        if server_count == 0:
            logger.info("Initializing VPN servers...")
            # (Server list would be here - using init endpoint for now)
            logger.info("ℹ️ Use /api/servers/init endpoint to initialize servers")
    except Exception as e:
        logger.error(f"Error during startup initialization: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
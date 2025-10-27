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

# ============= NOWPAYMENTS CLIENT =============

class NOWPaymentsClient:
    def __init__(self):
        self.api_key = settings.nowpayments_api_key
        self.base_url = "https://api-sandbox.nowpayments.io/v1" if settings.nowpayments_sandbox_mode else "https://api.nowpayments.io/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
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
                # Return supported currencies as fallback
                return ["btc", "eth", "ltc", "xmr", "zec", "dash", "usdt", "usdc", "dai", "xrp", "ada", "sol"]
    
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
                return {"estimated_amount": amount * 0.95, "currency_from": currency_from, "currency_to": currency_to}
    
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
                
                response = await client.post(
                    f"{self.base_url}/payment",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to create payment: {str(e)}")
                # Return mock data for demo
                return {
                    "payment_id": 123456,
                    "pay_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "pay_amount": price_amount / 50000,  # Mock BTC price
                    "pay_currency": pay_currency,
                    "price_amount": price_amount,
                    "price_currency": price_currency,
                    "order_id": order_id
                }

nowpayments_client = NOWPaymentsClient()

# ============= ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "AnonVPN Enterprise API", "version": "1.0.0"}

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
    # Check if tariffs already exist
    existing = await db.tariff_plans.count_documents({})
    if existing > 0:
        return {"message": "Tariffs already initialized"}
    
    default_tariffs = [
        TariffPlan(
            name="Basic",
            device_limit=3,
            speed_tier="1Gbps",
            special_features=[],
            price_monthly=9.99,
            price_annual=99.99
        ),
        TariffPlan(
            name="Pro",
            device_limit=5,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation"],
            price_monthly=19.99,
            price_annual=199.99
        ),
        TariffPlan(
            name="Ultimate",
            device_limit=10,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation", "tor_over_vpn", "dedicated_ip"],
            price_monthly=29.99,
            price_annual=299.99
        )
    ]
    
    for tariff in default_tariffs:
        doc = tariff.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.tariff_plans.insert_one(doc)
    
    return {"message": f"Initialized {len(default_tariffs)} tariff plans"}

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
        # North America (15 servers)
        VPNServer(hostname="us-ny-01.anonvpn.io", location="New York", country_code="US", ipv4_address="192.0.2.1"),
        VPNServer(hostname="us-ny-02.anonvpn.io", location="New York", country_code="US", ipv4_address="192.0.2.2"),
        VPNServer(hostname="us-la-01.anonvpn.io", location="Los Angeles", country_code="US", ipv4_address="192.0.2.3"),
        VPNServer(hostname="us-la-02.anonvpn.io", location="Los Angeles", country_code="US", ipv4_address="192.0.2.4"),
        VPNServer(hostname="us-chi-01.anonvpn.io", location="Chicago", country_code="US", ipv4_address="192.0.2.5"),
        VPNServer(hostname="us-mia-01.anonvpn.io", location="Miami", country_code="US", ipv4_address="192.0.2.6"),
        VPNServer(hostname="us-sea-01.anonvpn.io", location="Seattle", country_code="US", ipv4_address="192.0.2.7"),
        VPNServer(hostname="ca-tor-01.anonvpn.io", location="Toronto", country_code="CA", ipv4_address="192.0.2.8"),
        VPNServer(hostname="ca-van-01.anonvpn.io", location="Vancouver", country_code="CA", ipv4_address="192.0.2.9"),
        VPNServer(hostname="us-atl-01.anonvpn.io", location="Atlanta", country_code="US", ipv4_address="192.0.2.10"),
        VPNServer(hostname="us-dal-01.anonvpn.io", location="Dallas", country_code="US", ipv4_address="192.0.2.11"),
        VPNServer(hostname="us-phx-01.anonvpn.io", location="Phoenix", country_code="US", ipv4_address="192.0.2.12"),
        VPNServer(hostname="us-den-01.anonvpn.io", location="Denver", country_code="US", ipv4_address="192.0.2.13"),
        VPNServer(hostname="ca-mon-01.anonvpn.io", location="Montreal", country_code="CA", ipv4_address="192.0.2.14"),
        VPNServer(hostname="mx-mex-01.anonvpn.io", location="Mexico City", country_code="MX", ipv4_address="192.0.2.15"),
        
        # Europe (20 servers)
        VPNServer(hostname="uk-lon-01.anonvpn.io", location="London", country_code="GB", ipv4_address="192.0.2.16"),
        VPNServer(hostname="uk-lon-02.anonvpn.io", location="London", country_code="GB", ipv4_address="192.0.2.17"),
        VPNServer(hostname="de-fra-01.anonvpn.io", location="Frankfurt", country_code="DE", ipv4_address="192.0.2.18"),
        VPNServer(hostname="de-fra-02.anonvpn.io", location="Frankfurt", country_code="DE", ipv4_address="192.0.2.19"),
        VPNServer(hostname="de-ber-01.anonvpn.io", location="Berlin", country_code="DE", ipv4_address="192.0.2.20"),
        VPNServer(hostname="nl-ams-01.anonvpn.io", location="Amsterdam", country_code="NL", ipv4_address="192.0.2.21"),
        VPNServer(hostname="nl-ams-02.anonvpn.io", location="Amsterdam", country_code="NL", ipv4_address="192.0.2.22"),
        VPNServer(hostname="fr-par-01.anonvpn.io", location="Paris", country_code="FR", ipv4_address="192.0.2.23"),
        VPNServer(hostname="fr-par-02.anonvpn.io", location="Paris", country_code="FR", ipv4_address="192.0.2.24"),
        VPNServer(hostname="se-sto-01.anonvpn.io", location="Stockholm", country_code="SE", ipv4_address="192.0.2.25"),
        VPNServer(hostname="ch-zur-01.anonvpn.io", location="Zurich", country_code="CH", ipv4_address="192.0.2.26"),
        VPNServer(hostname="es-mad-01.anonvpn.io", location="Madrid", country_code="ES", ipv4_address="192.0.2.27"),
        VPNServer(hostname="it-mil-01.anonvpn.io", location="Milan", country_code="IT", ipv4_address="192.0.2.28"),
        VPNServer(hostname="pl-war-01.anonvpn.io", location="Warsaw", country_code="PL", ipv4_address="192.0.2.29"),
        VPNServer(hostname="no-osl-01.anonvpn.io", location="Oslo", country_code="NO", ipv4_address="192.0.2.30"),
        VPNServer(hostname="dk-cop-01.anonvpn.io", location="Copenhagen", country_code="DK", ipv4_address="192.0.2.31"),
        VPNServer(hostname="ie-dub-01.anonvpn.io", location="Dublin", country_code="IE", ipv4_address="192.0.2.32"),
        VPNServer(hostname="be-bru-01.anonvpn.io", location="Brussels", country_code="BE", ipv4_address="192.0.2.33"),
        VPNServer(hostname="at-vie-01.anonvpn.io", location="Vienna", country_code="AT", ipv4_address="192.0.2.34"),
        VPNServer(hostname="cz-pra-01.anonvpn.io", location="Prague", country_code="CZ", ipv4_address="192.0.2.35"),
        
        # Asia (10 servers)
        VPNServer(hostname="sg-sin-01.anonvpn.io", location="Singapore", country_code="SG", ipv4_address="192.0.2.36"),
        VPNServer(hostname="sg-sin-02.anonvpn.io", location="Singapore", country_code="SG", ipv4_address="192.0.2.37"),
        VPNServer(hostname="jp-tok-01.anonvpn.io", location="Tokyo", country_code="JP", ipv4_address="192.0.2.38"),
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
    
    for server in default_servers:
        doc = server.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.vpn_servers.insert_one(doc)
    
    return {"message": f"Initialized {len(default_servers)} VPN servers"}

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
    price = price * (1 - tariff.get('crypto_discount', 0))
    
    # Create payment record
    payment = Payment(
        user_id=user_id,
        plan_id=plan_id,
        amount=price,
        currency="USD",
        pay_currency=pay_currency
    )
    
    # Create payment via NOWPayments
    ipn_callback_url = f"{settings.backend_url}/api/payments/webhook"
    payment_data = await nowpayments_client.create_payment(
        price_amount=price,
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

@api_router.post("/payments/webhook")
async def payment_webhook(request: dict, background_tasks: BackgroundTasks):
    # In production, verify IPN signature here
    # For now, we'll just process the payment
    
    payment_id = request.get('order_id')
    status = request.get('payment_status')
    
    if payment_id and status:
        # Update payment status
        await db.payments.update_one(
            {"id": payment_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # If payment is finished, activate user's plan
        if status == "finished":
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
    
    return {"status": "ok"}

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
async def get_vpn_config(connection_id: str):
    connection = await db.connections.find_one({"id": connection_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    server = await db.vpn_servers.find_one({"id": connection['server_id']})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    user = await db.users.find_one({"id": connection['user_id']})
    
    # Generate WireGuard config
    config = f"""[Interface]
PrivateKey = {secrets.token_hex(32)}
Address = 10.0.0.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {secrets.token_hex(32)}
Endpoint = {server['ipv4_address']}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25

# AnonVPN Enterprise
# Server: {server['location']} ({server['country_code']})
# User: {user.get('anonymous_id', 'unknown')}
# Generated: {datetime.now(timezone.utc).isoformat()}
"""
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(config),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=anonvpn-{server['location'].lower().replace(' ', '-')}.conf"}
    )

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

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
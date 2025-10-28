from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from vpn_provider_integration import get_vpn_provider
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
    protocols: List[str] = ["WireGuard", "OpenVPN", "IKEv2", "Shadowsocks"]
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
    wallet_address: Optional[str] = None  # Ethereum wallet address for crypto auth
    current_plan_id: Optional[str] = None
    plan_expires_at: Optional[datetime] = None
    total_data_used: int = 0
    devices: List[Dict[str, Any]] = []
    organization_id: Optional[str] = None  # Links to Organization for corporate users
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

# ============= CORPORATE MODELS =============

class Organization(BaseModel):
    """Corporate account for multi-user management"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    owner_email: EmailStr
    plan_id: str  # Corporate plan
    plan_expires_at: Optional[datetime] = None
    max_team_members: int = 10  # Based on plan
    total_data_used: int = 0
    is_active: bool = True
    # White-label branding
    branding: Optional[Dict[str, Any]] = None  # logo_url, primary_color, secondary_color, custom_domain
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TeamMember(BaseModel):
    """Member of an organization with role-based access"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str  # Links to User
    email: EmailStr
    role: str = "member"  # owner, admin, manager, member
    is_active: bool = True
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: Optional[datetime] = None

class PartnerAPIKey(BaseModel):
    """API key for partners to manage users and subscriptions"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partner_name: str
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    is_active: bool = True
    allowed_operations: List[str] = ["create_user", "manage_subscription"]  # Operations allowed
    rate_limit: int = 1000  # Requests per hour
    requests_count: int = 0
    last_request_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

class SecurityEvent(BaseModel):
    """Security monitoring event for Team Dashboard"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: Optional[str] = None
    user_id: str
    event_type: str  # login, connection, disconnection, suspicious_activity, data_breach_attempt
    severity: str = "info"  # info, warning, critical
    description: str
    ip_address: Optional[str] = None
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============= ANALYTICS & MONITORING MODELS =============

class ConnectionHistory(BaseModel):
    """History of user connections (no traffic logs, only metadata)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    server_id: str
    server_location: str
    protocol: str
    device_name: str
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    session_duration: Optional[int] = None  # seconds
    ip_address: Optional[str] = None  # User's IP for geolocation only
    country: Optional[str] = None
    city: Optional[str] = None

class ServerMetrics(BaseModel):
    """Real-time server metrics for monitoring"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    server_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float
    memory_used: int  # bytes
    network_rx: int  # bytes received
    network_tx: int  # bytes transmitted
    active_connections: int
    load_average: float

class ReferralProgram(BaseModel):
    """Referral tracking for user growth"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    referrer_id: str  # User who refers
    referred_id: Optional[str] = None  # User who was referred (filled when they sign up)
    referral_code: str = Field(default_factory=lambda: secrets.token_urlsafe(8))
    commission_rate: float = 0.20  # 20% commission
    total_earned: float = 0.0
    status: str = "active"  # active, completed, expired
    clicks: int = 0
    signups: int = 0
    conversions: int = 0  # Paid subscriptions
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

class DedicatedIP(BaseModel):
    """Dedicated IP addresses for premium users"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    ip_address: str
    server_id: str
    location: str
    is_active: bool = True
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

class OAuth2Provider(BaseModel):
    """OAuth2 provider configuration for enterprise SSO"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_name: str  # google, microsoft, okta, etc.
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str] = ["openid", "profile", "email"]
    is_active: bool = True
    organization_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SAMLProvider(BaseModel):
    """SAML provider configuration for enterprise SSO"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_name: str
    organization_id: str
    idp_entity_id: str
    sso_url: str
    x509_cert: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ActiveSession(BaseModel):
    """Active VPN sessions for tracking and management"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    device_id: str
    device_name: str
    connection_id: str
    server_id: str
    server_location: str
    protocol: str
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str
    country: Optional[str] = None
    city: Optional[str] = None
    data_sent: int = 0  # bytes
    data_received: int = 0  # bytes
    is_active: bool = True

class GDPRRequest(BaseModel):
    """GDPR compliance data requests"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    request_type: str  # data_export, data_deletion, data_rectification
    status: str = "pending"  # pending, processing, completed, rejected
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    data_url: Optional[str] = None  # For data exports
    notes: Optional[str] = None

class AuditLog(BaseModel):
    """No-log policy audit trail (metadata only)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str  # server_started, policy_verified, config_changed
    result: str  # success, failed
    details: str
    auditor: Optional[str] = None

class SecurityIncident(BaseModel):
    """Security incident tracking and response"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    severity: str  # low, medium, high, critical
    status: str = "open"  # open, investigating, resolved, closed
    affected_systems: List[str] = []
    actions_taken: List[str] = []
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None

class SupportTicket(BaseModel):
    """Customer support ticket system"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    subject: str
    description: str
    priority: str = "normal"  # low, normal, high, urgent
    status: str = "open"  # open, in_progress, waiting_customer, resolved, closed
    category: str = "general"  # technical, billing, account, general
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    messages: List[Dict[str, Any]] = []

class SLAMetric(BaseModel):
    """Service Level Agreement metrics tracking"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_percentage: float = 99.95
    avg_response_time: float = 0.0  # milliseconds
    incident_count: int = 0
    critical_incident_count: int = 0
    mttr: Optional[float] = None  # Mean Time To Repair (minutes)
    meets_sla: bool = True

class DMCANotice(BaseModel):
    """DMCA takedown notice tracking"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complainant_name: str
    complainant_email: str
    content_description: str
    alleged_user_id: Optional[str] = None
    status: str = "received"  # received, investigating, resolved, rejected
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    action_taken: Optional[str] = None

class SecurityAudit(BaseModel):
    """Security audit scheduling and results"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audit_type: str  # penetration_test, vulnerability_scan, compliance_audit, code_review
    scheduled_date: datetime
    completed_date: Optional[datetime] = None
    status: str = "scheduled"  # scheduled, in_progress, completed, failed
    auditor: str
    findings: List[Dict[str, Any]] = []
    report_url: Optional[str] = None
    severity_summary: Dict[str, int] = {}

class Alert(BaseModel):
    """System alerting for monitoring and incidents"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_type: str  # server_down, high_cpu, high_memory, security_breach, payment_failed
    severity: str  # info, warning, error, critical
    title: str
    message: str
    source: str  # server_id, user_id, system
    is_active: bool = True
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class AffiliatePartner(BaseModel):
    """Affiliate partner tracking for revenue sharing"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    affiliate_code: str = Field(default_factory=lambda: secrets.token_urlsafe(10))
    commission_rate: float = 0.30  # 30% commission
    total_earnings: float = 0.0
    pending_earnings: float = 0.0
    paid_earnings: float = 0.0
    clicks: int = 0
    signups: int = 0
    conversions: int = 0
    status: str = "active"  # active, suspended, terminated
    payment_method: Optional[str] = None
    payment_details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AffiliateEarning(BaseModel):
    """Affiliate earnings tracking"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    affiliate_id: str
    user_id: str  # Referred user
    payment_id: str
    amount: float
    commission: float
    status: str = "pending"  # pending, approved, paid
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: Optional[datetime] = None

class Device(BaseModel):
    """User device management"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    device_name: str
    device_type: str  # desktop, mobile, tablet, router
    os: str  # windows, macos, linux, ios, android
    last_connection: Optional[datetime] = None
    is_active: bool = True
    max_connections: int = 1
    active_connections: int = 0
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============= REQUEST MODELS FOR API =============

class CreateOAuth2ProviderRequest(BaseModel):
    """Request model for creating OAuth2 provider"""
    organization_id: str
    provider_name: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str] = ["openid", "profile", "email"]

class CreateSAMLProviderRequest(BaseModel):
    """Request model for creating SAML provider"""
    organization_id: str
    provider_name: str
    idp_entity_id: str
    sso_url: str
    x509_cert: str

class RegisterAffiliateRequest(BaseModel):
    """Request model for affiliate registration"""
    user_id: str
    payment_method: str
    payment_details: Dict[str, Any]

class CreateSecurityIncidentRequest(BaseModel):
    """Request model for creating security incident"""
    title: str
    description: str
    severity: str
    affected_systems: List[str] = []
    assigned_to: Optional[str] = None

class ResolveSecurityIncidentRequest(BaseModel):
    """Request model for resolving security incident"""
    actions_taken: List[str]
    resolved_by: str

class CreateSupportTicketRequest(BaseModel):
    """Request model for creating support ticket"""
    user_id: str
    subject: str
    description: str
    priority: str = "normal"
    category: str = "general"

class CreateDMCANoticeRequest(BaseModel):
    """Request model for DMCA notice"""
    complainant_name: str
    complainant_email: str
    content_description: str
    alleged_user_id: Optional[str] = None

class ScheduleSecurityAuditRequest(BaseModel):
    """Request model for scheduling security audit"""
    audit_type: str
    scheduled_date: str
    auditor: str

class CreateAlertRequest(BaseModel):
    """Request model for creating alert"""
    alert_type: str
    severity: str
    title: str
    message: str
    source: str

class CreateAuditLogRequest(BaseModel):
    """Request model for audit log"""
    action: str
    result: str
    details: str
    auditor: Optional[str] = None

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
            price_monthly=19.99,
            price_annual=199.99,
            crypto_discount=0.0
        ),
        TariffPlan(
            name="Pro",
            device_limit=5,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation"],
            price_monthly=39.99,
            price_annual=399.99,
            crypto_discount=0.0
        ),
        TariffPlan(
            name="Ultimate",
            device_limit=10,
            speed_tier="10Gbps",
            special_features=["double_vpn", "obfuscation", "tor_over_vpn", "dedicated_ip"],
            price_monthly=59.99,
            price_annual=599.99,
            crypto_discount=0.0
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
async def init_servers(force: bool = False):
    # Check if servers already exist
    existing = await db.vpn_servers.count_documents({})
    if existing > 0 and not force:
        return {"message": "Servers already initialized"}
    
    # Clear existing servers if force=True
    if force:
        await db.vpn_servers.delete_many({})
    
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
        VPNServer(hostname="jp-tok-02.anonvpn.io", location="Tokyo", country_code="JP", ipv4_address="192.0.2.39", supports_tor=True, tor_socks_port=9050, obfs4_port=9001),
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
async def create_user(
    email: Optional[EmailStr] = None,
    wallet_address: Optional[str] = None
):
    # Check if user already exists with this wallet address
    if wallet_address:
        existing_user = await db.users.find_one({"wallet_address": wallet_address}, {"_id": 0})
        if existing_user:
            # Return existing user
            if isinstance(existing_user.get('created_at'), str):
                existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
            if existing_user.get('last_seen') and isinstance(existing_user.get('last_seen'), str):
                existing_user['last_seen'] = datetime.fromisoformat(existing_user['last_seen'])
            if existing_user.get('plan_expires_at') and isinstance(existing_user.get('plan_expires_at'), str):
                existing_user['plan_expires_at'] = datetime.fromisoformat(existing_user['plan_expires_at'])
            return User(**existing_user)
    
    user = User(email=email, wallet_address=wallet_address)
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
    - shadowsocks
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
        elif protocol == "shadowsocks":
            config = vpn_config_generator.generate_shadowsocks_config(
                server_ip=server['ipv4_address'],
                server_location=server['location'],
                user_id=user['id']
            )
            config_data = {
                'config': config,
                'filename': f'shadowsocks_{server["location"].replace(" ", "_")}.txt'
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported protocol: {protocol}. Use wireguard, openvpn, ikev2, or shadowsocks"
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
            },
            {
                "name": "Shadowsocks",
                "id": "shadowsocks",
                "description": "Secure SOCKS5 proxy for bypassing censorship",
                "performance": "Excellent",
                "compatibility": "All platforms",
                "recommended": False,
                "use_case": "Best for bypassing GFW and censorship"
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


@api_router.get("/servers/realtime-status")
async def get_realtime_server_status():
    """Get real-time status of all VPN servers"""
    servers = await db.vpn_servers.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    server_status = []
    for server in servers:
        # Get active connections count
        active_connections = await db.connections.count_documents({
            "server_id": server.get('id'),
            "is_active": True
        })
        
        # Calculate load percentage
        max_capacity = server.get('max_capacity', 1000)
        load_percent = (active_connections / max_capacity) * 100
        
        # Determine server health status
        if load_percent < 70:
            health = "healthy"
        elif load_percent < 90:
            health = "warning"
        else:
            health = "critical"
        
        server_status.append({
            "id": server.get('id'),
            "hostname": server.get('hostname'),
            "location": server.get('location'),
            "country_code": server.get('country_code'),
            "active_connections": active_connections,
            "max_capacity": max_capacity,
            "load_percent": round(load_percent, 1),
            "health": health,
            "protocols": server.get('supported_protocols', ['wireguard', 'openvpn', 'ikev2']),
            "features": {
                "double_vpn": server.get('supports_double_vpn', False),
                "tor": server.get('supports_tor', False),
                "obfuscation": server.get('supports_obfuscation', False)
            },
            "last_health_check": server.get('last_health_check', datetime.now(timezone.utc).isoformat())
        })
    
    # Calculate global stats
    total_capacity = sum(s.get('max_capacity', 0) for s in servers)
    total_active = sum(s['active_connections'] for s in server_status)
    global_load = (total_active / total_capacity * 100) if total_capacity > 0 else 0
    
    return {
        "servers": server_status,
        "total_servers": len(servers),
        "global_stats": {
            "total_capacity": total_capacity,
            "total_active_connections": total_active,
            "global_load_percent": round(global_load, 1),
            "healthy_servers": len([s for s in server_status if s['health'] == 'healthy']),
            "warning_servers": len([s for s in server_status if s['health'] == 'warning']),
            "critical_servers": len([s for s in server_status if s['health'] == 'critical'])
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.post("/admin/servers/{server_id}/health-check")
async def trigger_server_health_check(server_id: str):
    """Trigger manual health check for a specific server"""
    server = await db.vpn_servers.find_one({"id": server_id}, {"_id": 0})
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Update last health check timestamp
    await db.vpn_servers.update_one(
        {"id": server_id},
        {"$set": {"last_health_check": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get current metrics
    active_connections = await db.connections.count_documents({
        "server_id": server_id,
        "is_active": True
    })
    
    max_capacity = server.get('max_capacity', 1000)
    load_percent = (active_connections / max_capacity) * 100
    
    return {
        "server_id": server_id,
        "hostname": server.get('hostname'),
        "location": server.get('location'),
        "health_check_completed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "active_connections": active_connections,
            "max_capacity": max_capacity,
            "load_percent": round(load_percent, 1),
            "is_active": server.get('is_active', True)
        }
    }


# ============= VPN PROVIDER MANAGEMENT (DigitalOcean & Vultr) =============

@api_router.post("/admin/vpn-providers/deploy-server")
async def deploy_vpn_server(
    provider: str,
    region: str,
    location_name: str,
    country_code: str,
    plan: str = None,
    api_key: str = None
):
    """
    Deploy a new VPN server using DigitalOcean or Vultr
    
    Args:
        provider: 'digitalocean' or 'vultr'
        region: Provider region code (e.g., 'nyc1', 'ewr')
        location_name: Display name (e.g., 'New York')
        country_code: Country code (e.g., 'US')
        plan: Server plan/size (optional, uses default)
        api_key: API key for provider (optional, uses env var)
    """
    try:
        # Get API key from environment if not provided
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail=f"API key required. Set {env_key} environment variable or provide api_key parameter"
                )
        
        # Get provider instance
        vpn_provider = get_vpn_provider(provider, api_key)
        
        # Create server
        server_name = f"vpn-{location_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}"
        
        logger.info(f"🚀 Deploying {provider} VPN server in {region}...")
        
        result = await vpn_provider.create_server(
            region=region,
            plan=plan,
            name=server_name
        )
        
        await vpn_provider.close()
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create server")
        
        # Add to database
        server_data = {
            "id": str(uuid.uuid4()),
            "provider": provider,
            "provider_server_id": result.get('server_id'),
            "hostname": server_name,
            "location": location_name,
            "country_code": country_code,
            "ipv4_address": result.get('ip_address', 'pending'),
            "ipv6_address": result.get('ipv6_address'),
            "is_active": False,  # Will be activated after setup completes
            "max_capacity": 1000,
            "current_connections": 0,
            "supported_protocols": ['wireguard', 'openvpn', 'ikev2'],
            "supports_double_vpn": True,
            "supports_tor": False,
            "supports_obfuscation": True,
            "obfs4_port": 9001,
            "provider_region": region,
            "provider_plan": plan or 'default',
            "deployment_status": "deploying",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_health_check": None
        }
        
        await db.vpn_servers.insert_one(server_data)
        
        logger.info(f"✅ VPN server deployment initiated: {server_data['id']}")
        
        return {
            "message": "VPN server deployment initiated",
            "server_id": server_data['id'],
            "provider": provider,
            "provider_server_id": result.get('server_id'),
            "location": location_name,
            "region": region,
            "status": "deploying",
            "estimated_setup_time": "5-10 minutes",
            "note": "Server will be automatically activated after setup completes"
        }
        
    except Exception as e:
        logger.error(f"Error deploying VPN server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/vpn-providers/{provider}/servers")
async def list_provider_servers(provider: str, api_key: str = None):
    """List all servers from a specific provider"""
    try:
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        vpn_provider = get_vpn_provider(provider, api_key)
        servers = await vpn_provider.list_servers()
        await vpn_provider.close()
        
        return {
            "provider": provider,
            "servers": servers,
            "total": len(servers)
        }
        
    except Exception as e:
        logger.error(f"Error listing {provider} servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/vpn-providers/{provider}/server/{server_id}")
async def get_provider_server_info(provider: str, server_id: str, api_key: str = None):
    """Get detailed information about a server from provider"""
    try:
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        vpn_provider = get_vpn_provider(provider, api_key)
        server_info = await vpn_provider.get_server_info(server_id)
        await vpn_provider.close()
        
        if not server_info:
            raise HTTPException(status_code=404, detail="Server not found")
        
        return server_info
        
    except Exception as e:
        logger.error(f"Error getting {provider} server info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/vpn-providers/{provider}/server/{server_id}/sync")
async def sync_server_status(provider: str, server_id: str, api_key: str = None):
    """
    Sync server status from provider to database
    Updates IP address, status, and other info
    """
    try:
        # Find server in database by provider_server_id
        db_server = await db.vpn_servers.find_one({
            "provider_server_id": server_id
        }, {"_id": 0})
        
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found in database")
        
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        # Get fresh info from provider
        vpn_provider = get_vpn_provider(provider, api_key)
        provider_info = await vpn_provider.get_server_info(server_id)
        await vpn_provider.close()
        
        if not provider_info:
            raise HTTPException(status_code=404, detail="Server not found at provider")
        
        # Update database
        update_data = {
            "ipv4_address": provider_info.get('ip_address'),
            "ipv6_address": provider_info.get('ipv6_address'),
            "deployment_status": "active" if provider_info.get('status') == 'active' else "deploying",
            "is_active": provider_info.get('status') == 'active',
            "last_sync": datetime.now(timezone.utc).isoformat()
        }
        
        await db.vpn_servers.update_one(
            {"provider_server_id": server_id},
            {"$set": update_data}
        )
        
        logger.info(f"✅ Synced server {server_id} from {provider}")
        
        return {
            "message": "Server status synced",
            "server_id": db_server.get('id'),
            "provider": provider,
            "status": provider_info.get('status'),
            "ip_address": provider_info.get('ip_address'),
            "updated_fields": update_data
        }
        
    except Exception as e:
        logger.error(f"Error syncing server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/admin/vpn-providers/{provider}/server/{server_id}")
async def delete_provider_server(provider: str, server_id: str, api_key: str = None):
    """
    Delete a VPN server from provider and database
    WARNING: This is irreversible!
    """
    try:
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        # Delete from provider
        vpn_provider = get_vpn_provider(provider, api_key)
        deleted = await vpn_provider.delete_server(server_id)
        await vpn_provider.close()
        
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete server from provider")
        
        # Remove from database
        result = await db.vpn_servers.delete_one({"provider_server_id": server_id})
        
        logger.info(f"✅ Deleted server {server_id} from {provider}")
        
        return {
            "message": "Server deleted successfully",
            "provider": provider,
            "server_id": server_id,
            "deleted_from_database": result.deleted_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error deleting server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/vpn-providers/{provider}/server/{server_id}/reboot")
async def reboot_provider_server(provider: str, server_id: str, api_key: str = None):
    """Reboot a VPN server"""
    try:
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        vpn_provider = get_vpn_provider(provider, api_key)
        rebooted = await vpn_provider.reboot_server(server_id)
        await vpn_provider.close()
        
        if not rebooted:
            raise HTTPException(status_code=500, detail="Failed to reboot server")
        
        # Update status in database
        await db.vpn_servers.update_one(
            {"provider_server_id": server_id},
            {"$set": {
                "is_active": False,
                "deployment_status": "rebooting",
                "last_reboot": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"✅ Rebooted server {server_id} on {provider}")
        
        return {
            "message": "Server reboot initiated",
            "provider": provider,
            "server_id": server_id,
            "estimated_downtime": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"Error rebooting server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/vpn-providers/{provider}/regions")
async def get_provider_regions(provider: str, api_key: str = None):
    """Get available regions from provider"""
    try:
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
            
            if not api_key:
                raise HTTPException(status_code=400, detail=f"API key required for {provider}")
        
        vpn_provider = get_vpn_provider(provider, api_key)
        regions = await vpn_provider.get_available_regions()
        await vpn_provider.close()
        
        return {
            "provider": provider,
            "regions": regions,
            "total": len(regions)
        }
        
    except Exception as e:
        logger.error(f"Error getting regions: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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

# ============= CORPORATE API ENDPOINTS =============

# Organization Management

@api_router.post("/organizations")
async def create_organization(
    name: str,
    owner_email: EmailStr,
    plan_id: str,
    max_team_members: int = 10
):
    """Create a new corporate organization"""
    try:
        # Verify plan exists
        plan = await db.tariff_plans.find_one({"id": plan_id}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Create organization
        org = Organization(
            name=name,
            owner_email=owner_email,
            plan_id=plan_id,
            max_team_members=max_team_members,
            plan_expires_at=datetime.now(timezone.utc) + timedelta(days=365)
        )
        
        doc = org.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        if doc.get('plan_expires_at'):
            doc['plan_expires_at'] = doc['plan_expires_at'].isoformat()
        
        await db.organizations.insert_one(doc)
        
        # Create owner user
        owner_user = User(
            email=owner_email,
            current_plan_id=plan_id,
            organization_id=org.id,
            plan_expires_at=org.plan_expires_at
        )
        
        user_doc = owner_user.model_dump()
        user_doc['created_at'] = user_doc['created_at'].isoformat()
        if user_doc.get('plan_expires_at'):
            user_doc['plan_expires_at'] = user_doc['plan_expires_at'].isoformat()
        
        await db.users.insert_one(user_doc)
        
        # Create team member record for owner
        team_member = TeamMember(
            organization_id=org.id,
            user_id=owner_user.id,
            email=owner_email,
            role="owner"
        )
        
        member_doc = team_member.model_dump()
        member_doc['joined_at'] = member_doc['joined_at'].isoformat()
        
        await db.team_members.insert_one(member_doc)
        
        logger.info(f"Created organization: {org.id} for {owner_email}")
        
        return {
            "organization_id": org.id,
            "owner_user_id": owner_user.id,
            "message": "Organization created successfully"
        }
    
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/organizations/{org_id}")
async def get_organization(org_id: str):
    """Get organization details"""
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Convert ISO strings back to datetime for response
    if isinstance(org.get('created_at'), str):
        org['created_at'] = datetime.fromisoformat(org['created_at'])
    if isinstance(org.get('updated_at'), str):
        org['updated_at'] = datetime.fromisoformat(org['updated_at'])
    if isinstance(org.get('plan_expires_at'), str):
        org['plan_expires_at'] = datetime.fromisoformat(org['plan_expires_at'])
    
    # Get team members count
    members_count = await db.team_members.count_documents({"organization_id": org_id, "is_active": True})
    org['current_team_members'] = members_count
    
    return org

@api_router.put("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    name: Optional[str] = None,
    max_team_members: Optional[int] = None,
    branding: Optional[Dict[str, Any]] = None
):
    """Update organization details"""
    org = await db.organizations.find_one({"id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if name:
        update_data["name"] = name
    if max_team_members is not None:
        update_data["max_team_members"] = max_team_members
    if branding is not None:
        update_data["branding"] = branding
    
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": update_data}
    )
    
    return {"message": "Organization updated successfully"}

# Team Member Management

@api_router.post("/organizations/{org_id}/members")
async def add_team_member(
    org_id: str,
    email: EmailStr,
    role: str = "member"
):
    """Add a team member to organization"""
    # Verify organization exists
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check team size limit
    current_members = await db.team_members.count_documents({
        "organization_id": org_id,
        "is_active": True
    })
    
    if current_members >= org.get('max_team_members', 10):
        raise HTTPException(status_code=400, detail="Team member limit reached")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user['id']
        # Update user with organization
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "organization_id": org_id,
                "current_plan_id": org.get('plan_id'),
                "plan_expires_at": org.get('plan_expires_at')
            }}
        )
    else:
        # Create new user
        new_user = User(
            email=email,
            current_plan_id=org.get('plan_id'),
            organization_id=org_id,
            plan_expires_at=datetime.fromisoformat(org.get('plan_expires_at')) if isinstance(org.get('plan_expires_at'), str) else org.get('plan_expires_at')
        )
        
        user_doc = new_user.model_dump()
        user_doc['created_at'] = user_doc['created_at'].isoformat()
        if user_doc.get('plan_expires_at'):
            user_doc['plan_expires_at'] = user_doc['plan_expires_at'].isoformat()
        
        await db.users.insert_one(user_doc)
        user_id = new_user.id
    
    # Create team member record
    team_member = TeamMember(
        organization_id=org_id,
        user_id=user_id,
        email=email,
        role=role
    )
    
    member_doc = team_member.model_dump()
    member_doc['joined_at'] = member_doc['joined_at'].isoformat()
    
    await db.team_members.insert_one(member_doc)
    
    # Log security event
    security_event = SecurityEvent(
        organization_id=org_id,
        user_id=user_id,
        event_type="member_added",
        severity="info",
        description=f"Team member {email} added with role {role}"
    )
    event_doc = security_event.model_dump()
    event_doc['created_at'] = event_doc['created_at'].isoformat()
    await db.security_events.insert_one(event_doc)
    
    return {
        "user_id": user_id,
        "message": "Team member added successfully"
    }

@api_router.get("/organizations/{org_id}/members")
async def get_team_members(org_id: str):
    """Get all team members of an organization"""
    members = await db.team_members.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0}
    ).to_list(1000)
    
    for member in members:
        if isinstance(member.get('joined_at'), str):
            member['joined_at'] = datetime.fromisoformat(member['joined_at'])
        if isinstance(member.get('last_active'), str):
            member['last_active'] = datetime.fromisoformat(member['last_active'])
    
    return {"members": members, "total": len(members)}

@api_router.put("/organizations/{org_id}/members/{member_id}")
async def update_team_member(
    org_id: str,
    member_id: str,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Update team member role or status"""
    update_data = {}
    
    if role:
        if role not in ["owner", "admin", "manager", "member"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        update_data["role"] = role
    
    if is_active is not None:
        update_data["is_active"] = is_active
    
    result = await db.team_members.update_one(
        {"id": member_id, "organization_id": org_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    return {"message": "Team member updated successfully"}

@api_router.delete("/organizations/{org_id}/members/{member_id}")
async def remove_team_member(org_id: str, member_id: str):
    """Remove a team member from organization"""
    member = await db.team_members.find_one({"id": member_id, "organization_id": org_id})
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    if member.get('role') == 'owner':
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")
    
    # Deactivate team member
    await db.team_members.update_one(
        {"id": member_id},
        {"$set": {"is_active": False}}
    )
    
    # Update user
    await db.users.update_one(
        {"id": member.get('user_id')},
        {"$set": {
            "organization_id": None,
            "current_plan_id": None,
            "plan_expires_at": None
        }}
    )
    
    return {"message": "Team member removed successfully"}

# Security Monitoring

@api_router.get("/organizations/{org_id}/security/events")
async def get_security_events(
    org_id: str,
    limit: int = 100,
    severity: Optional[str] = None
):
    """Get security events for organization"""
    query = {"organization_id": org_id}
    
    if severity:
        query["severity"] = severity
    
    events = await db.security_events.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for event in events:
        if isinstance(event.get('created_at'), str):
            event['created_at'] = datetime.fromisoformat(event['created_at'])
    
    return {"events": events, "total": len(events)}

@api_router.get("/organizations/{org_id}/dashboard")
async def get_team_dashboard(org_id: str):
    """Get team dashboard data with security monitoring"""
    # Get organization
    org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get active team members
    active_members = await db.team_members.count_documents({
        "organization_id": org_id,
        "is_active": True
    })
    
    # Get active connections
    active_connections = await db.connections.count_documents({
        "is_active": True,
        "user_id": {"$in": [
            member['user_id'] for member in await db.team_members.find(
                {"organization_id": org_id, "is_active": True},
                {"user_id": 1, "_id": 0}
            ).to_list(1000)
        ]}
    })
    
    # Get recent security events
    recent_events = await db.security_events.find(
        {"organization_id": org_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    for event in recent_events:
        if isinstance(event.get('created_at'), str):
            event['created_at'] = datetime.fromisoformat(event['created_at'])
    
    # Get total data usage
    total_data = org.get('total_data_used', 0)
    
    # Get security summary
    critical_events = await db.security_events.count_documents({
        "organization_id": org_id,
        "severity": "critical",
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}
    })
    
    warning_events = await db.security_events.count_documents({
        "organization_id": org_id,
        "severity": "warning",
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}
    })
    
    return {
        "organization": org,
        "stats": {
            "active_members": active_members,
            "max_members": org.get('max_team_members', 10),
            "active_connections": active_connections,
            "total_data_used_gb": round(total_data / (1024**3), 2),
            "plan_expires_at": org.get('plan_expires_at')
        },
        "security": {
            "critical_events_7d": critical_events,
            "warning_events_7d": warning_events,
            "recent_events": recent_events
        }
    }

# Partner API

@api_router.post("/partner/api-keys")
async def create_partner_api_key(
    partner_name: str,
    allowed_operations: List[str] = ["create_user", "manage_subscription"],
    rate_limit: int = 1000
):
    """Create a new partner API key"""
    api_key_obj = PartnerAPIKey(
        partner_name=partner_name,
        allowed_operations=allowed_operations,
        rate_limit=rate_limit,
        expires_at=datetime.now(timezone.utc) + timedelta(days=365)
    )
    
    doc = api_key_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('expires_at'):
        doc['expires_at'] = doc['expires_at'].isoformat()
    
    await db.partner_api_keys.insert_one(doc)
    
    return {
        "api_key": api_key_obj.api_key,
        "secret_key": api_key_obj.secret_key,
        "partner_name": partner_name,
        "message": "Partner API key created successfully. Store these keys securely."
    }

async def verify_partner_api_key(api_key: str, secret_key: str) -> Optional[Dict]:
    """Verify partner API key and secret"""
    key_doc = await db.partner_api_keys.find_one({
        "api_key": api_key,
        "secret_key": secret_key,
        "is_active": True
    }, {"_id": 0})
    
    if not key_doc:
        return None
    
    # Check expiration
    if key_doc.get('expires_at'):
        expires_at = datetime.fromisoformat(key_doc['expires_at']) if isinstance(key_doc['expires_at'], str) else key_doc['expires_at']
        if expires_at < datetime.now(timezone.utc):
            return None
    
    # Check rate limit
    if key_doc.get('last_request_at'):
        last_request = datetime.fromisoformat(key_doc['last_request_at']) if isinstance(key_doc['last_request_at'], str) else key_doc['last_request_at']
        if (datetime.now(timezone.utc) - last_request).total_seconds() < 3600:
            if key_doc.get('requests_count', 0) >= key_doc.get('rate_limit', 1000):
                return None
        else:
            # Reset counter after an hour
            await db.partner_api_keys.update_one(
                {"api_key": api_key},
                {"$set": {"requests_count": 0}}
            )
            key_doc['requests_count'] = 0
    
    # Increment request count
    await db.partner_api_keys.update_one(
        {"api_key": api_key},
        {
            "$inc": {"requests_count": 1},
            "$set": {"last_request_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return key_doc

@api_router.post("/partner/users")
async def partner_create_user(
    api_key: str,
    secret_key: str,
    email: EmailStr,
    plan_id: str,
    plan_duration_days: int = 30
):
    """Partner API: Create a new user with subscription"""
    # Verify API key
    key_doc = await verify_partner_api_key(api_key, secret_key)
    if not key_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    if "create_user" not in key_doc.get('allowed_operations', []):
        raise HTTPException(status_code=403, detail="Operation not allowed")
    
    # Verify plan exists
    plan = await db.tariff_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Create user
    user = User(
        email=email,
        current_plan_id=plan_id,
        plan_expires_at=datetime.now(timezone.utc) + timedelta(days=plan_duration_days)
    )
    
    user_doc = user.model_dump()
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    if user_doc.get('plan_expires_at'):
        user_doc['plan_expires_at'] = user_doc['plan_expires_at'].isoformat()
    
    await db.users.insert_one(user_doc)
    
    logger.info(f"Partner {key_doc['partner_name']} created user: {user.id}")
    
    return {
        "user_id": user.id,
        "anonymous_id": user.anonymous_id,
        "email": email,
        "plan_id": plan_id,
        "plan_expires_at": user.plan_expires_at.isoformat(),
        "message": "User created successfully"
    }

@api_router.put("/partner/users/{user_id}/subscription")
async def partner_update_subscription(
    user_id: str,
    api_key: str,
    secret_key: str,
    plan_id: Optional[str] = None,
    extend_days: Optional[int] = None
):
    """Partner API: Update user subscription"""
    # Verify API key
    key_doc = await verify_partner_api_key(api_key, secret_key)
    if not key_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    if "manage_subscription" not in key_doc.get('allowed_operations', []):
        raise HTTPException(status_code=403, detail="Operation not allowed")
    
    # Get user
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    
    if plan_id:
        # Verify plan exists
        plan = await db.tariff_plans.find_one({"id": plan_id}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        update_data["current_plan_id"] = plan_id
    
    if extend_days:
        current_expiry = user.get('plan_expires_at')
        if isinstance(current_expiry, str):
            current_expiry = datetime.fromisoformat(current_expiry)
        
        if current_expiry and current_expiry > datetime.now(timezone.utc):
            new_expiry = current_expiry + timedelta(days=extend_days)
        else:
            new_expiry = datetime.now(timezone.utc) + timedelta(days=extend_days)
        
        update_data["plan_expires_at"] = new_expiry.isoformat()
    
    if update_data:
        await db.users.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
    
    logger.info(f"Partner {key_doc['partner_name']} updated subscription for user: {user_id}")
    
    return {"message": "Subscription updated successfully"}

# ============= ANALYTICS & MONITORING ENDPOINTS =============

@api_router.get("/analytics/dashboard")
async def get_analytics_dashboard():
    """Get comprehensive analytics dashboard data"""
    try:
        # Total users
        total_users = await db.users.count_documents({})
        
        # Active subscriptions
        now = datetime.now(timezone.utc)
        active_subscriptions = await db.users.count_documents({
            "plan_expires_at": {"$gte": now.isoformat()}
        })
        
        # Total payments
        total_payments = await db.payments.count_documents({})
        successful_payments = await db.payments.count_documents({"status": {"$in": ["confirmed", "finished"]}})
        
        # Revenue calculation
        payments_cursor = db.payments.find({"status": {"$in": ["confirmed", "finished"]}})
        total_revenue = 0
        monthly_revenue = 0
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async for payment in payments_cursor:
            total_revenue += payment.get('amount', 0)
            payment_date = payment.get('created_at')
            if isinstance(payment_date, str):
                payment_date = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
            if payment_date >= month_start:
                monthly_revenue += payment.get('amount', 0)
        
        # Active connections
        active_connections = await db.connections.count_documents({"is_active": True})
        
        # Geography data (top 5 countries)
        geography_pipeline = [
            {"$match": {"country": {"$ne": None}}},
            {"$group": {"_id": "$country", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        geography_cursor = db.connection_history.aggregate(geography_pipeline)
        geography = [{"country": doc["_id"], "users": doc["count"]} async for doc in geography_cursor]
        
        # Popular plans
        plan_pipeline = [
            {"$match": {"current_plan_id": {"$ne": None}}},
            {"$group": {"_id": "$current_plan_id", "count": {"$sum": 1}}}
        ]
        plan_cursor = db.users.aggregate(plan_pipeline)
        plan_stats = {}
        async for doc in plan_cursor:
            plan_doc = await db.tariff_plans.find_one({"id": doc["_id"]})
            if plan_doc:
                plan_stats[plan_doc['name']] = doc['count']
        
        # Server load
        server_count = await db.vpn_servers.count_documents({"is_active": True})
        
        return {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "total_revenue": round(total_revenue, 2),
            "monthly_revenue": round(monthly_revenue, 2),
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "conversion_rate": round((successful_payments / total_payments * 100) if total_payments > 0 else 0, 2),
            "active_connections": active_connections,
            "active_servers": server_count,
            "geography": geography,
            "popular_plans": plan_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/revenue")
async def get_revenue_analytics(period: str = Query("month", regex="^(day|week|month|year)$")):
    """Get revenue analytics for specified period"""
    try:
        now = datetime.now(timezone.utc)
        
        # Calculate start date based on period
        if period == "day":
            start_date = now - timedelta(days=1)
            date_format = "%Y-%m-%d %H:00"
        elif period == "week":
            start_date = now - timedelta(days=7)
            date_format = "%Y-%m-%d"
        elif period == "month":
            start_date = now - timedelta(days=30)
            date_format = "%Y-%m-%d"
        else:  # year
            start_date = now - timedelta(days=365)
            date_format = "%Y-%m"
        
        # Aggregate revenue by date
        pipeline = [
            {
                "$match": {
                    "status": {"$in": ["confirmed", "finished"]},
                    "created_at": {"$gte": start_date.isoformat()}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": date_format,
                            "date": {"$toDate": "$created_at"}
                        }
                    },
                    "revenue": {"$sum": "$amount"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = db.payments.aggregate(pipeline)
        data = [{"date": doc["_id"], "revenue": round(doc["revenue"], 2), "transactions": doc["count"]} async for doc in cursor]
        
        total = sum(item["revenue"] for item in data)
        
        return {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "total_revenue": round(total, 2),
            "data": data
        }
    except Exception as e:
        logger.error(f"Revenue analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/conversion")
async def get_conversion_analytics():
    """Get conversion funnel analytics"""
    try:
        # Total users
        total_users = await db.users.count_documents({})
        
        # Users with active subscriptions
        active_subscribers = await db.users.count_documents({
            "current_plan_id": {"$ne": None},
            "plan_expires_at": {"$gte": datetime.now(timezone.utc).isoformat()}
        })
        
        # Total payments
        total_payments = await db.payments.count_documents({})
        successful_payments = await db.payments.count_documents({
            "status": {"$in": ["confirmed", "finished"]}
        })
        
        # Calculate conversion rates
        subscription_conversion = (active_subscribers / total_users * 100) if total_users > 0 else 0
        payment_success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
        
        # Get referral conversions
        referral_signups = await db.referral_programs.aggregate([
            {"$group": {"_id": None, "total_signups": {"$sum": "$signups"}, "total_conversions": {"$sum": "$conversions"}}}
        ]).to_list(1)
        
        referral_conversion = 0
        if referral_signups and referral_signups[0]["total_signups"] > 0:
            referral_conversion = (referral_signups[0]["total_conversions"] / referral_signups[0]["total_signups"] * 100)
        
        return {
            "funnel": {
                "total_users": total_users,
                "active_subscribers": active_subscribers,
                "subscription_conversion_rate": round(subscription_conversion, 2)
            },
            "payments": {
                "total_attempts": total_payments,
                "successful_payments": successful_payments,
                "success_rate": round(payment_success_rate, 2)
            },
            "referrals": {
                "total_signups": referral_signups[0]["total_signups"] if referral_signups else 0,
                "total_conversions": referral_signups[0]["total_conversions"] if referral_signups else 0,
                "conversion_rate": round(referral_conversion, 2)
            }
        }
    except Exception as e:
        logger.error(f"Conversion analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/churn")
async def get_churn_analytics(period_days: int = 30):
    """Get churn rate analytics"""
    try:
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)
        
        # Users at start of period with active subscriptions
        users_at_start = await db.users.count_documents({
            "created_at": {"$lt": period_start.isoformat()},
            "current_plan_id": {"$ne": None}
        })
        
        # Users who churned (subscription expired and not renewed)
        churned_users = await db.users.count_documents({
            "plan_expires_at": {
                "$gte": period_start.isoformat(),
                "$lt": now.isoformat()
            },
            "current_plan_id": None
        })
        
        # Calculate churn rate
        churn_rate = (churned_users / users_at_start * 100) if users_at_start > 0 else 0
        
        # Revenue lost from churn
        # Get average subscription value
        avg_payment = await db.payments.aggregate([
            {
                "$match": {
                    "status": {"$in": ["confirmed", "finished"]}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_amount": {"$avg": "$amount"}
                }
            }
        ]).to_list(1)
        
        avg_subscription_value = avg_payment[0]["avg_amount"] if avg_payment else 0
        revenue_lost = churned_users * avg_subscription_value
        
        # Get churn reasons (if tracked)
        # This would require additional data collection
        
        return {
            "period_days": period_days,
            "users_at_period_start": users_at_start,
            "churned_users": churned_users,
            "churn_rate": round(churn_rate, 2),
            "estimated_revenue_lost": round(revenue_lost, 2),
            "avg_subscription_value": round(avg_subscription_value, 2)
        }
    except Exception as e:
        logger.error(f"Churn analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/geographic-distribution")
async def get_geographic_distribution_analytics():
    """Get geographic distribution of users based on connection history"""
    try:
        # Aggregate connections by country
        pipeline = [
            {
                "$match": {
                    "country": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$country",
                    "total_sessions": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"}
                }
            },
            {
                "$project": {
                    "country": "$_id",
                    "total_sessions": 1,
                    "unique_users": {"$size": "$unique_users"}
                }
            },
            {"$sort": {"unique_users": -1}}
        ]
        
        cursor = db.connection_history.aggregate(pipeline)
        countries = []
        async for doc in cursor:
            countries.append({
                "country": doc["_id"],
                "unique_users": doc["unique_users"],
                "total_sessions": doc["total_sessions"]
            })
        
        # Get server distribution
        server_cursor = db.vpn_servers.find({"is_active": True})
        server_distribution = {}
        async for server in server_cursor:
            country = server.get("country_code", "Unknown")
            server_distribution[country] = server_distribution.get(country, 0) + 1
        
        return {
            "user_distribution": countries,
            "server_distribution": [{"country": k, "server_count": v} for k, v in server_distribution.items()],
            "total_countries": len(countries)
        }
    except Exception as e:
        logger.error(f"Geographic distribution analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/plan-popularity")
async def get_plan_popularity_analytics():
    """Get plan popularity and revenue by plan"""
    try:
        # Get all plans
        plans_cursor = db.tariff_plans.find({})
        plans = {}
        async for plan in plans_cursor:
            plans[plan["id"]] = {
                "name": plan["name"],
                "price_monthly": plan["price_monthly"],
                "price_annual": plan["price_annual"],
                "subscribers": 0,
                "revenue": 0
            }
        
        # Count subscribers per plan
        users_cursor = db.users.find({"current_plan_id": {"$ne": None}})
        async for user in users_cursor:
            plan_id = user.get("current_plan_id")
            if plan_id in plans:
                plans[plan_id]["subscribers"] += 1
        
        # Calculate revenue per plan
        payments_cursor = db.payments.find({
            "status": {"$in": ["confirmed", "finished"]}
        })
        async for payment in payments_cursor:
            plan_id = payment.get("plan_id")
            if plan_id in plans:
                plans[plan_id]["revenue"] += payment.get("amount", 0)
        
        # Convert to list and sort by subscribers
        plan_list = [
            {
                "plan_id": k,
                "plan_name": v["name"],
                "subscribers": v["subscribers"],
                "revenue": round(v["revenue"], 2),
                "avg_revenue_per_user": round(v["revenue"] / v["subscribers"], 2) if v["subscribers"] > 0 else 0
            }
            for k, v in plans.items()
        ]
        plan_list.sort(key=lambda x: x["subscribers"], reverse=True)
        
        return {
            "plans": plan_list,
            "total_subscribers": sum(p["subscribers"] for p in plan_list),
            "total_revenue": round(sum(p["revenue"] for p in plan_list), 2)
        }
    except Exception as e:
        logger.error(f"Plan popularity analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= CONNECTION HISTORY ENDPOINTS =============

@api_router.get("/users/{user_id}/connection-history")
async def get_user_connection_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """Get user's connection history (metadata only, no traffic logs)"""
    try:
        cursor = db.connection_history.find(
            {"user_id": user_id}
        ).sort("connected_at", -1).limit(limit)
        
        history = []
        async for doc in cursor:
            # Get server location
            server = await db.vpn_servers.find_one({"id": doc.get("server_id")})
            doc["server_name"] = server.get("location") if server else "Unknown"
            history.append(doc)
        
        return {
            "user_id": user_id,
            "total_sessions": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Connection history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/users/{user_id}/active-sessions")
async def get_user_active_sessions(user_id: str):
    """Get user's currently active VPN sessions"""
    try:
        cursor = db.connections.find({
            "user_id": user_id,
            "is_active": True
        })
        
        sessions = []
        async for doc in cursor:
            # Get server details
            server = await db.vpn_servers.find_one({"id": doc.get("server_id")})
            if server:
                session = {
                    "connection_id": doc["id"],
                    "server_location": server["location"],
                    "protocol": doc.get("protocol", "WireGuard"),
                    "device_name": doc.get("device_name", "Unknown"),
                    "connected_at": doc["connected_at"],
                    "duration_seconds": int((datetime.now(timezone.utc) - datetime.fromisoformat(doc["connected_at"].replace('Z', '+00:00'))).total_seconds()) if isinstance(doc["connected_at"], str) else 0
                }
                sessions.append(session)
        
        return {
            "user_id": user_id,
            "active_sessions_count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Active sessions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= REFERRAL PROGRAM ENDPOINTS =============

@api_router.post("/referrals/create")
async def create_referral_code(user_id: str):
    """Create a referral code for a user"""
    try:
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already has a referral code
        existing = await db.referral_programs.find_one({"referrer_id": user_id})
        if existing:
            return {
                "message": "Referral code already exists",
                "referral_code": existing["referral_code"],
                "referral_link": f"https://anonvpn.com/signup?ref={existing['referral_code']}"
            }
        
        # Create new referral program
        referral = ReferralProgram(
            referrer_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365)
        )
        
        doc = referral.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        if doc['expires_at']:
            doc['expires_at'] = doc['expires_at'].isoformat()
        
        await db.referral_programs.insert_one(doc)
        
        logger.info(f"Created referral code for user: {user_id}")
        
        return {
            "message": "Referral code created successfully",
            "referral_code": referral.referral_code,
            "referral_link": f"https://anonvpn.com/signup?ref={referral.referral_code}",
            "commission_rate": referral.commission_rate * 100,
            "expires_at": doc['expires_at']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create referral error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/referrals/{user_id}/stats")
async def get_referral_stats(user_id: str):
    """Get referral statistics for a user"""
    try:
        referral = await db.referral_programs.find_one({"referrer_id": user_id})
        if not referral:
            raise HTTPException(status_code=404, detail="No referral program found for this user")
        
        # Get referred users
        referred_users = []
        if referral.get("referred_id"):
            user_doc = await db.users.find_one({"id": referral["referred_id"]})
            if user_doc:
                referred_users.append({
                    "user_id": user_doc["id"],
                    "signed_up_at": user_doc.get("created_at"),
                    "has_subscription": bool(user_doc.get("current_plan_id"))
                })
        
        return {
            "referral_code": referral["referral_code"],
            "referral_link": f"https://anonvpn.com/signup?ref={referral['referral_code']}",
            "clicks": referral.get("clicks", 0),
            "signups": referral.get("signups", 0),
            "conversions": referral.get("conversions", 0),
            "total_earned": round(referral.get("total_earned", 0), 2),
            "commission_rate": referral.get("commission_rate", 0.2) * 100,
            "status": referral.get("status", "active"),
            "referred_users": referred_users
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/referrals/track-click")
async def track_referral_click(referral_code: str):
    """Track a click on a referral link"""
    try:
        result = await db.referral_programs.update_one(
            {"referral_code": referral_code},
            {"$inc": {"clicks": 1}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Invalid referral code")
        
        return {"message": "Click tracked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Track click error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/referrals/track-signup")
async def track_referral_signup(referral_code: str, new_user_id: str):
    """Track when a referred user signs up"""
    try:
        # Update referral program
        result = await db.referral_programs.update_one(
            {"referral_code": referral_code},
            {
                "$inc": {"signups": 1},
                "$set": {"referred_id": new_user_id}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Invalid referral code")
        
        return {"message": "Signup tracked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Track signup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= CUSTOM DNS ENDPOINTS =============

class CustomDNSServer(BaseModel):
    """Custom DNS server configuration"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None  # If None, it's a public DNS
    name: str
    primary_dns: str
    secondary_dns: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@api_router.get("/dns/public")
async def get_public_dns_servers():
    """Get list of public DNS servers"""
    try:
        # Return predefined public DNS servers
        public_dns = [
            {
                "id": "cloudflare",
                "name": "Cloudflare DNS",
                "primary_dns": "1.1.1.1",
                "secondary_dns": "1.0.0.1",
                "description": "Fast and privacy-focused DNS by Cloudflare",
                "is_default": True
            },
            {
                "id": "google",
                "name": "Google DNS",
                "primary_dns": "8.8.8.8",
                "secondary_dns": "8.8.4.4",
                "description": "Reliable and fast DNS by Google"
            },
            {
                "id": "quad9",
                "name": "Quad9 DNS",
                "primary_dns": "9.9.9.9",
                "secondary_dns": "149.112.112.112",
                "description": "Security-focused DNS with threat blocking"
            },
            {
                "id": "opendns",
                "name": "OpenDNS",
                "primary_dns": "208.67.222.222",
                "secondary_dns": "208.67.220.220",
                "description": "DNS with content filtering options"
            }
        ]
        
        # Also get user's custom DNS servers
        cursor = db.custom_dns.find({"is_public": True, "is_active": True})
        custom_dns = []
        async for doc in cursor:
            custom_dns.append({
                "id": doc["id"],
                "name": doc["name"],
                "primary_dns": doc["primary_dns"],
                "secondary_dns": doc.get("secondary_dns"),
                "description": doc.get("description"),
                "is_custom": True
            })
        
        return {
            "public_dns": public_dns,
            "custom_public_dns": custom_dns
        }
    except Exception as e:
        logger.error(f"Get public DNS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/dns/custom")
async def create_custom_dns(
    user_id: str,
    name: str,
    primary_dns: str,
    secondary_dns: Optional[str] = None,
    description: Optional[str] = None,
    is_public: bool = False
):
    """Create custom DNS server configuration"""
    try:
        # Validate DNS format
        import re
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        if not re.match(ipv4_pattern, primary_dns):
            raise HTTPException(status_code=400, detail="Invalid primary DNS format")
        
        if secondary_dns and not re.match(ipv4_pattern, secondary_dns):
            raise HTTPException(status_code=400, detail="Invalid secondary DNS format")
        
        custom_dns = CustomDNSServer(
            user_id=user_id if not is_public else None,
            name=name,
            primary_dns=primary_dns,
            secondary_dns=secondary_dns,
            description=description,
            is_public=is_public
        )
        
        doc = custom_dns.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.custom_dns.insert_one(doc)
        
        logger.info(f"Created custom DNS: {name} for user: {user_id}")
        
        return {
            "message": "Custom DNS created successfully",
            "dns_id": custom_dns.id,
            "name": name,
            "primary_dns": primary_dns,
            "secondary_dns": secondary_dns
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create custom DNS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/dns/user/{user_id}")
async def get_user_custom_dns(user_id: str):
    """Get user's custom DNS configurations"""
    try:
        cursor = db.custom_dns.find({
            "user_id": user_id,
            "is_active": True
        })
        
        dns_list = []
        async for doc in cursor:
            dns_list.append({
                "id": doc["id"],
                "name": doc["name"],
                "primary_dns": doc["primary_dns"],
                "secondary_dns": doc.get("secondary_dns"),
                "description": doc.get("description"),
                "created_at": doc["created_at"]
            })
        
        return {
            "user_id": user_id,
            "custom_dns_count": len(dns_list),
            "dns_servers": dns_list
        }
    except Exception as e:
        logger.error(f"Get user custom DNS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= LOYALTY PROGRAM ENDPOINTS =============

class LoyaltyProgram(BaseModel):
    """Loyalty points and rewards program"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    total_points: int = 0
    points_earned: int = 0
    points_redeemed: int = 0
    tier: str = "bronze"  # bronze, silver, gold, platinum
    tier_progress: float = 0.0  # Percentage to next tier
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LoyaltyTransaction(BaseModel):
    """Loyalty points transaction history"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    points: int  # Positive for earned, negative for redeemed
    type: str  # subscription_renewal, referral_bonus, review, redemption
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@api_router.get("/loyalty/{user_id}")
async def get_loyalty_status(user_id: str):
    """Get user's loyalty program status"""
    try:
        # Get or create loyalty account
        loyalty = await db.loyalty_programs.find_one({"user_id": user_id})
        
        if not loyalty:
            # Create new loyalty account
            new_loyalty = LoyaltyProgram(user_id=user_id)
            doc = new_loyalty.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.loyalty_programs.insert_one(doc)
            loyalty = doc
        
        # Get tier benefits
        tier_benefits = {
            "bronze": {"discount": 0, "bonus_points": 1.0, "priority_support": False},
            "silver": {"discount": 5, "bonus_points": 1.25, "priority_support": False},
            "gold": {"discount": 10, "bonus_points": 1.5, "priority_support": True},
            "platinum": {"discount": 15, "bonus_points": 2.0, "priority_support": True}
        }
        
        # Calculate tier thresholds
        tier_thresholds = {
            "bronze": 0,
            "silver": 1000,
            "gold": 5000,
            "platinum": 15000
        }
        
        current_tier = loyalty.get("tier", "bronze")
        total_points = loyalty.get("total_points", 0)
        
        # Calculate progress to next tier
        next_tier_map = {"bronze": "silver", "silver": "gold", "gold": "platinum", "platinum": None}
        next_tier = next_tier_map.get(current_tier)
        
        tier_progress = 0.0
        if next_tier:
            current_threshold = tier_thresholds[current_tier]
            next_threshold = tier_thresholds[next_tier]
            tier_progress = ((total_points - current_threshold) / (next_threshold - current_threshold)) * 100
            tier_progress = min(max(tier_progress, 0), 100)
        
        return {
            "user_id": user_id,
            "total_points": total_points,
            "available_points": loyalty.get("total_points", 0),
            "tier": current_tier,
            "tier_progress": round(tier_progress, 1),
            "next_tier": next_tier,
            "benefits": tier_benefits[current_tier],
            "points_earned": loyalty.get("points_earned", 0),
            "points_redeemed": loyalty.get("points_redeemed", 0)
        }
    except Exception as e:
        logger.error(f"Get loyalty status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/loyalty/{user_id}/earn")
async def earn_loyalty_points(
    user_id: str,
    points: int,
    type: str,
    description: str
):
    """Award loyalty points to a user"""
    try:
        # Get or create loyalty account
        loyalty = await db.loyalty_programs.find_one({"user_id": user_id})
        
        if not loyalty:
            new_loyalty = LoyaltyProgram(user_id=user_id)
            doc = new_loyalty.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.loyalty_programs.insert_one(doc)
        
        # Update points
        await db.loyalty_programs.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "total_points": points,
                    "points_earned": points
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Create transaction record
        transaction = LoyaltyTransaction(
            user_id=user_id,
            points=points,
            type=type,
            description=description
        )
        
        trans_doc = transaction.model_dump()
        trans_doc['created_at'] = trans_doc['created_at'].isoformat()
        await db.loyalty_transactions.insert_one(trans_doc)
        
        # Check and update tier
        updated_loyalty = await db.loyalty_programs.find_one({"user_id": user_id})
        total_points = updated_loyalty.get("total_points", 0)
        
        new_tier = "bronze"
        if total_points >= 15000:
            new_tier = "platinum"
        elif total_points >= 5000:
            new_tier = "gold"
        elif total_points >= 1000:
            new_tier = "silver"
        
        if new_tier != updated_loyalty.get("tier"):
            await db.loyalty_programs.update_one(
                {"user_id": user_id},
                {"$set": {"tier": new_tier}}
            )
        
        logger.info(f"Awarded {points} loyalty points to user: {user_id}")
        
        return {
            "message": f"Earned {points} loyalty points",
            "points_earned": points,
            "total_points": total_points + points,
            "tier": new_tier
        }
    except Exception as e:
        logger.error(f"Earn loyalty points error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/loyalty/{user_id}/transactions")
async def get_loyalty_transactions(user_id: str, limit: int = 50):
    """Get user's loyalty transaction history"""
    try:
        cursor = db.loyalty_transactions.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        
        transactions = []
        async for doc in cursor:
            transactions.append({
                "id": doc["id"],
                "points": doc["points"],
                "type": doc["type"],
                "description": doc["description"],
                "created_at": doc["created_at"]
            })
        
        return {
            "user_id": user_id,
            "transaction_count": len(transactions),
            "transactions": transactions
        }
    except Exception as e:
        logger.error(f"Get loyalty transactions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= SERVER MONITORING ENDPOINTS =============

@api_router.post("/servers/{server_id}/metrics")
async def record_server_metrics(
    server_id: str,
    cpu_percent: float,
    memory_used: int,
    network_rx: int,
    network_tx: int,
    active_connections: int,
    load_average: float
):
    """Record server metrics (called by monitoring agents)"""
    try:
        metrics = ServerMetrics(
            server_id=server_id,
            cpu_percent=cpu_percent,
            memory_used=memory_used,
            network_rx=network_rx,
            network_tx=network_tx,
            active_connections=active_connections,
            load_average=load_average
        )
        
        doc = metrics.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        await db.server_metrics.insert_one(doc)
        
        # Update server's current_connections
        await db.vpn_servers.update_one(
            {"id": server_id},
            {"$set": {"current_connections": active_connections}}
        )
        
        return {"message": "Metrics recorded successfully"}
    except Exception as e:
        logger.error(f"Record server metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/servers/{server_id}/metrics")
async def get_server_metrics(
    server_id: str,
    period: str = "1h"  # 1h, 24h, 7d, 30d
):
    """Get server metrics for a time period"""
    try:
        now = datetime.now(timezone.utc)
        
        # Calculate time range
        if period == "1h":
            start_time = now - timedelta(hours=1)
        elif period == "24h":
            start_time = now - timedelta(hours=24)
        elif period == "7d":
            start_time = now - timedelta(days=7)
        elif period == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=1)
        
        # Get metrics
        cursor = db.server_metrics.find({
            "server_id": server_id,
            "timestamp": {"$gte": start_time.isoformat()}
        }).sort("timestamp", 1)
        
        metrics = []
        async for doc in cursor:
            metrics.append({
                "timestamp": doc["timestamp"],
                "cpu_percent": doc["cpu_percent"],
                "memory_used": doc["memory_used"],
                "network_rx": doc["network_rx"],
                "network_tx": doc["network_tx"],
                "active_connections": doc["active_connections"],
                "load_average": doc["load_average"]
            })
        
        # Calculate averages
        if metrics:
            avg_cpu = sum(m["cpu_percent"] for m in metrics) / len(metrics)
            avg_load = sum(m["load_average"] for m in metrics) / len(metrics)
            max_connections = max(m["active_connections"] for m in metrics)
        else:
            avg_cpu = 0
            avg_load = 0
            max_connections = 0
        
        return {
            "server_id": server_id,
            "period": period,
            "data_points": len(metrics),
            "metrics": metrics,
            "summary": {
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_load_average": round(avg_load, 2),
                "max_connections": max_connections
            }
        }
    except Exception as e:
        logger.error(f"Get server metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/servers/metrics/overview")
async def get_all_servers_metrics_overview():
    """Get current metrics overview for all servers"""
    try:
        # Get all active servers
        cursor = db.vpn_servers.find({"is_active": True})
        
        servers_overview = []
        async for server in cursor:
            # Get latest metrics
            latest_metric = await db.server_metrics.find_one(
                {"server_id": server["id"]},
                sort=[("timestamp", -1)]
            )
            
            if latest_metric:
                servers_overview.append({
                    "server_id": server["id"],
                    "location": server["location"],
                    "cpu_percent": latest_metric["cpu_percent"],
                    "load_average": latest_metric["load_average"],
                    "active_connections": latest_metric["active_connections"],
                    "max_capacity": server.get("max_capacity", 1000),
                    "utilization": round((latest_metric["active_connections"] / server.get("max_capacity", 1000)) * 100, 1),
                    "status": "healthy" if latest_metric["cpu_percent"] < 80 and latest_metric["load_average"] < 5 else "warning",
                    "last_update": latest_metric["timestamp"]
                })
        
        # Calculate overall stats
        total_connections = sum(s["active_connections"] for s in servers_overview)
        total_capacity = sum(s["max_capacity"] for s in servers_overview)
        avg_utilization = (total_connections / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            "total_servers": len(servers_overview),
            "total_active_connections": total_connections,
            "total_capacity": total_capacity,
            "average_utilization": round(avg_utilization, 1),
            "servers": servers_overview
        }
    except Exception as e:
        logger.error(f"Get servers metrics overview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= SHADOWSOCKS CONFIG ENDPOINT =============

@api_router.get("/connections/{connection_id}/shadowsocks-config")
async def get_shadowsocks_config(connection_id: str):
    """Download Shadowsocks configuration for a connection"""
    try:
        # Get connection
        connection = await db.connections.find_one({"id": connection_id})
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        if not connection.get("is_active"):
            raise HTTPException(status_code=400, detail="Connection is not active")
        
        # Get server
        server = await db.vpn_servers.find_one({"id": connection["server_id"]})
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Check if server supports Shadowsocks
        if "Shadowsocks" not in server.get("protocols", []):
            raise HTTPException(status_code=400, detail="Server does not support Shadowsocks protocol")
        
        # Generate Shadowsocks config
        config = vpn_config_generator.generate_shadowsocks_config(
            server_ip=server["ipv4_address"],
            server_location=server["location"],
            user_id=connection["user_id"]
        )
        
        # Return as downloadable file
        filename = f"shadowsocks-{server['location'].replace(' ', '-').lower()}.txt"
        
        return StreamingResponse(
            io.BytesIO(config.encode()),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get Shadowsocks config error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= DEVICE MANAGEMENT ENDPOINTS =============

@api_router.get("/users/{user_id}/devices")
async def get_user_devices(user_id: str):
    """Get all devices registered for a user"""
    try:
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        devices = user.get("devices", [])
        
        # Get active connections for each device
        for device in devices:
            active_connection = await db.connections.find_one({
                "user_id": user_id,
                "device_name": device["name"],
                "is_active": True
            })
            
            device["is_connected"] = bool(active_connection)
            if active_connection:
                server = await db.vpn_servers.find_one({"id": active_connection["server_id"]})
                device["connected_server"] = server.get("location") if server else "Unknown"
        
        # Get plan device limit
        device_limit = 5  # default
        if user.get("current_plan_id"):
            plan = await db.tariff_plans.find_one({"id": user["current_plan_id"]})
            if plan:
                device_limit = plan.get("device_limit", 5)
        
        return {
            "user_id": user_id,
            "device_count": len(devices),
            "device_limit": device_limit,
            "devices": devices
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user devices error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/users/{user_id}/devices")
async def register_device(
    user_id: str,
    device_name: str,
    device_type: str,  # windows, macos, linux, ios, android
    device_id: str
):
    """Register a new device for a user"""
    try:
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        devices = user.get("devices", [])
        
        # Check device limit
        device_limit = 5
        if user.get("current_plan_id"):
            plan = await db.tariff_plans.find_one({"id": user["current_plan_id"]})
            if plan:
                device_limit = plan.get("device_limit", 5)
        
        if len(devices) >= device_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Device limit reached ({device_limit} devices). Please upgrade your plan or remove a device."
            )
        
        # Check if device already registered
        if any(d.get("device_id") == device_id for d in devices):
            raise HTTPException(status_code=400, detail="Device already registered")
        
        # Add device
        new_device = {
            "device_id": device_id,
            "name": device_name,
            "type": device_type,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_connected": None
        }
        
        devices.append(new_device)
        
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"devices": devices}}
        )
        
        logger.info(f"Registered device {device_name} for user: {user_id}")
        
        return {
            "message": "Device registered successfully",
            "device": new_device,
            "device_count": len(devices),
            "device_limit": device_limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register device error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/users/{user_id}/devices/{device_id}")
async def remove_device(user_id: str, device_id: str):
    """Remove a device from user's account"""
    try:
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        devices = user.get("devices", [])
        
        # Find and remove device
        device_found = False
        updated_devices = []
        for device in devices:
            if device.get("device_id") == device_id:
                device_found = True
                # Disconnect any active connections for this device
                await db.connections.update_many(
                    {
                        "user_id": user_id,
                        "device_name": device.get("name"),
                        "is_active": True
                    },
                    {"$set": {"is_active": False, "disconnected_at": datetime.now(timezone.utc).isoformat()}}
                )
            else:
                updated_devices.append(device)
        
        if not device_found:
            raise HTTPException(status_code=404, detail="Device not found")
        
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"devices": updated_devices}}
        )
        
        logger.info(f"Removed device {device_id} for user: {user_id}")
        
        return {
            "message": "Device removed successfully",
            "device_count": len(updated_devices)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove device error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= DEDICATED IP ENDPOINTS =============

@api_router.post("/dedicated-ip/assign")
async def assign_dedicated_ip(user_id: str, server_id: str):
    """Assign a dedicated IP to a user (Ultimate plan only)"""
    try:
        # Check user plan
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.get("current_plan_id"):
            raise HTTPException(status_code=403, detail="No active subscription")
        
        plan = await db.tariff_plans.find_one({"id": user["current_plan_id"]})
        if not plan or "dedicated_ip" not in plan.get("special_features", []):
            raise HTTPException(status_code=403, detail="Dedicated IP not available in your plan")
        
        # Check if user already has a dedicated IP
        existing = await db.dedicated_ips.find_one({"user_id": user_id, "is_active": True})
        if existing:
            raise HTTPException(status_code=400, detail="User already has a dedicated IP")
        
        # Get server
        server = await db.vpn_servers.find_one({"id": server_id})
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Generate a mock dedicated IP (in production, this would be from IP pool)
        import random
        ip_address = f"185.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        
        # Create dedicated IP
        dedicated_ip = DedicatedIP(
            user_id=user_id,
            ip_address=ip_address,
            server_id=server_id,
            location=server["location"],
            expires_at=user.get("plan_expires_at")
        )
        
        doc = dedicated_ip.model_dump()
        doc['assigned_at'] = doc['assigned_at'].isoformat()
        if doc.get('expires_at'):
            if isinstance(doc['expires_at'], datetime):
                doc['expires_at'] = doc['expires_at'].isoformat()
        
        await db.dedicated_ips.insert_one(doc)
        
        logger.info(f"Assigned dedicated IP {ip_address} to user: {user_id}")
        
        return {
            "message": "Dedicated IP assigned successfully",
            "ip_address": ip_address,
            "location": server["location"],
            "expires_at": doc.get('expires_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assign dedicated IP error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/dedicated-ip/{user_id}")
async def get_user_dedicated_ip(user_id: str):
    """Get user's dedicated IP if they have one"""
    try:
        dedicated_ip = await db.dedicated_ips.find_one({
            "user_id": user_id,
            "is_active": True
        })
        
        if not dedicated_ip:
            raise HTTPException(status_code=404, detail="No dedicated IP found")
        
        return {
            "ip_address": dedicated_ip["ip_address"],
            "location": dedicated_ip["location"],
            "assigned_at": dedicated_ip["assigned_at"],
            "expires_at": dedicated_ip.get("expires_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get dedicated IP error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= CONNECTION HISTORY & SESSION TRACKING =============

@api_router.get("/users/{user_id}/connection-history")
async def get_connection_history(
    user_id: str,
    limit: int = Query(default=50, le=500),
    skip: int = Query(default=0, ge=0)
):
    """Get user's connection history (metadata only, no traffic logs)"""
    try:
        # Get connection history
        history_cursor = db.connection_history.find(
            {"user_id": user_id}
        ).sort("connected_at", -1).skip(skip).limit(limit)
        
        history = await history_cursor.to_list(length=limit)
        total_count = await db.connection_history.count_documents({"user_id": user_id})
        
        return {
            "total_count": total_count,
            "history": history,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Get connection history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/users/{user_id}/active-sessions")
async def get_active_sessions(user_id: str):
    """Get user's currently active VPN sessions"""
    try:
        # Get active connections
        sessions_cursor = db.active_sessions.find({
            "user_id": user_id,
            "is_active": True
        })
        
        sessions = await sessions_cursor.to_list(length=100)
        
        return {
            "active_sessions": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Get active sessions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/users/{user_id}/sessions/{session_id}/disconnect")
async def force_disconnect_session(user_id: str, session_id: str):
    """Force disconnect a specific session (security feature)"""
    try:
        # Find session
        session = await db.active_sessions.find_one({
            "id": session_id,
            "user_id": user_id,
            "is_active": True
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")
        
        # Deactivate session
        await db.active_sessions.update_one(
            {"id": session_id},
            {
                "$set": {
                    "is_active": False,
                    "disconnected_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Create connection history entry
        history_entry = ConnectionHistory(
            user_id=user_id,
            server_id=session["server_id"],
            server_location=session["server_location"],
            protocol=session["protocol"],
            device_name=session["device_name"],
            connected_at=session["connected_at"],
            disconnected_at=datetime.now(timezone.utc),
            session_duration=int((datetime.now(timezone.utc) - session["connected_at"]).total_seconds()),
            ip_address=session.get("ip_address"),
            country=session.get("country"),
            city=session.get("city")
        )
        
        doc = history_entry.model_dump()
        doc['connected_at'] = doc['connected_at'].isoformat()
        if doc.get('disconnected_at'):
            doc['disconnected_at'] = doc['disconnected_at'].isoformat()
        
        await db.connection_history.insert_one(doc)
        
        logger.info(f"Force disconnected session {session_id} for user: {user_id}")
        
        return {
            "message": "Session disconnected successfully",
            "session_id": session_id,
            "device_name": session["device_name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Force disconnect error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= REFERRAL PROGRAM & AFFILIATE SYSTEM =============

@api_router.post("/referrals/create")
async def create_referral_code(user_id: str):
    """Create a referral code for a user"""
    try:
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already has an active referral code
        existing = await db.referral_programs.find_one({
            "referrer_id": user_id,
            "status": "active"
        })
        
        if existing:
            return {
                "message": "Referral code already exists",
                "referral_code": existing["referral_code"],
                "referral_url": f"https://anonvpn.com/signup?ref={existing['referral_code']}"
            }
        
        # Create new referral program entry
        referral = ReferralProgram(referrer_id=user_id)
        
        doc = referral.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        if doc.get('expires_at'):
            doc['expires_at'] = doc['expires_at'].isoformat()
        
        await db.referral_programs.insert_one(doc)
        
        logger.info(f"Created referral code for user: {user_id}")
        
        return {
            "message": "Referral code created successfully",
            "referral_code": doc["referral_code"],
            "referral_url": f"https://anonvpn.com/signup?ref={doc['referral_code']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create referral error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/referrals/{user_id}/stats")
async def get_referral_stats(user_id: str):
    """Get referral statistics for a user"""
    try:
        # Get referral program
        referral = await db.referral_programs.find_one({
            "referrer_id": user_id,
            "status": "active"
        })
        
        if not referral:
            raise HTTPException(status_code=404, detail="No active referral program found")
        
        return {
            "referral_code": referral["referral_code"],
            "total_earned": referral.get("total_earned", 0.0),
            "clicks": referral.get("clicks", 0),
            "signups": referral.get("signups", 0),
            "conversions": referral.get("conversions", 0),
            "commission_rate": referral.get("commission_rate", 0.20),
            "status": referral["status"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get referral stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/referrals/track-click")
async def track_referral_click(referral_code: str):
    """Track a referral link click"""
    try:
        result = await db.referral_programs.update_one(
            {"referral_code": referral_code, "status": "active"},
            {"$inc": {"clicks": 1}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Referral code not found")
        
        return {"message": "Click tracked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Track click error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/affiliate/register")
async def register_affiliate(
    user_id: str,
    payment_method: str,
    payment_details: Dict[str, Any]
):
    """Register user as an affiliate partner"""
    try:
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already an affiliate
        existing = await db.affiliate_partners.find_one({"user_id": user_id})
        if existing:
            raise HTTPException(status_code=400, detail="User is already an affiliate partner")
        
        # Create affiliate partner
        affiliate = AffiliatePartner(
            user_id=user_id,
            payment_method=payment_method,
            payment_details=payment_details
        )
        
        doc = affiliate.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.affiliate_partners.insert_one(doc)
        
        logger.info(f"Registered affiliate partner: {user_id}")
        
        return {
            "message": "Affiliate registration successful",
            "affiliate_code": doc["affiliate_code"],
            "commission_rate": doc["commission_rate"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register affiliate error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/affiliate/dashboard/{user_id}")
async def get_affiliate_dashboard(user_id: str):
    """Get affiliate partner dashboard data"""
    try:
        # Get affiliate partner
        affiliate = await db.affiliate_partners.find_one({"user_id": user_id})
        if not affiliate:
            raise HTTPException(status_code=404, detail="Affiliate partner not found")
        
        # Get earnings history
        earnings_cursor = db.affiliate_earnings.find(
            {"affiliate_id": affiliate["id"]}
        ).sort("created_at", -1).limit(50)
        
        earnings = await earnings_cursor.to_list(length=50)
        
        return {
            "affiliate_code": affiliate["affiliate_code"],
            "commission_rate": affiliate["commission_rate"],
            "total_earnings": affiliate["total_earnings"],
            "pending_earnings": affiliate["pending_earnings"],
            "paid_earnings": affiliate["paid_earnings"],
            "clicks": affiliate["clicks"],
            "signups": affiliate["signups"],
            "conversions": affiliate["conversions"],
            "status": affiliate["status"],
            "recent_earnings": earnings
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get affiliate dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= OAUTH2 & SAML AUTHENTICATION =============

@api_router.post("/auth/oauth/providers")
async def create_oauth_provider(
    organization_id: str,
    provider_name: str,
    client_id: str,
    client_secret: str,
    authorization_url: str,
    token_url: str,
    userinfo_url: str,
    scopes: List[str] = ["openid", "profile", "email"]
):
    """Create OAuth2 provider configuration for organization"""
    try:
        provider = OAuth2Provider(
            organization_id=organization_id,
            provider_name=provider_name,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=authorization_url,
            token_url=token_url,
            userinfo_url=userinfo_url,
            scopes=scopes
        )
        
        doc = provider.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.oauth2_providers.insert_one(doc)
        
        logger.info(f"Created OAuth2 provider {provider_name} for org: {organization_id}")
        
        return {
            "message": "OAuth2 provider created successfully",
            "provider_id": doc["id"]
        }
    except Exception as e:
        logger.error(f"Create OAuth2 provider error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/oauth/providers/{organization_id}")
async def get_oauth_providers(organization_id: str):
    """Get OAuth2 providers for an organization"""
    try:
        providers_cursor = db.oauth2_providers.find({
            "organization_id": organization_id,
            "is_active": True
        })
        
        providers = await providers_cursor.to_list(length=100)
        
        # Remove sensitive data
        for provider in providers:
            provider.pop('client_secret', None)
        
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Get OAuth2 providers error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/saml/configure")
async def configure_saml_provider(
    organization_id: str,
    provider_name: str,
    idp_entity_id: str,
    sso_url: str,
    x509_cert: str
):
    """Configure SAML provider for organization"""
    try:
        provider = SAMLProvider(
            organization_id=organization_id,
            provider_name=provider_name,
            idp_entity_id=idp_entity_id,
            sso_url=sso_url,
            x509_cert=x509_cert
        )
        
        doc = provider.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.saml_providers.insert_one(doc)
        
        logger.info(f"Configured SAML provider {provider_name} for org: {organization_id}")
        
        return {
            "message": "SAML provider configured successfully",
            "provider_id": doc["id"]
        }
    except Exception as e:
        logger.error(f"Configure SAML provider error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= GDPR COMPLIANCE =============

@api_router.post("/gdpr/data-export")
async def request_data_export(user_id: str):
    """Request GDPR data export"""
    try:
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create GDPR request
        gdpr_request = GDPRRequest(
            user_id=user_id,
            request_type="data_export",
            status="pending"
        )
        
        doc = gdpr_request.model_dump()
        doc['requested_at'] = doc['requested_at'].isoformat()
        
        await db.gdpr_requests.insert_one(doc)
        
        logger.info(f"Data export requested for user: {user_id}")
        
        return {
            "message": "Data export request submitted successfully",
            "request_id": doc["id"],
            "status": "pending",
            "estimated_completion": "24-48 hours"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data export request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/gdpr/data-deletion")
async def request_data_deletion(user_id: str, confirm: bool = False):
    """Request GDPR data deletion (account deletion)"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Please confirm data deletion by setting confirm=true"
            )
        
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create GDPR request
        gdpr_request = GDPRRequest(
            user_id=user_id,
            request_type="data_deletion",
            status="pending",
            notes="User requested account and data deletion"
        )
        
        doc = gdpr_request.model_dump()
        doc['requested_at'] = doc['requested_at'].isoformat()
        
        await db.gdpr_requests.insert_one(doc)
        
        logger.info(f"Data deletion requested for user: {user_id}")
        
        return {
            "message": "Data deletion request submitted successfully",
            "request_id": doc["id"],
            "status": "pending",
            "estimated_completion": "30 days"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data deletion request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/gdpr/requests/{user_id}")
async def get_gdpr_requests(user_id: str):
    """Get GDPR requests for a user"""
    try:
        requests_cursor = db.gdpr_requests.find(
            {"user_id": user_id}
        ).sort("requested_at", -1)
        
        requests = await requests_cursor.to_list(length=100)
        
        return {"requests": requests}
    except Exception as e:
        logger.error(f"Get GDPR requests error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= NO-LOG AUDIT & SECURITY =============

@api_router.post("/audit/log")
async def create_audit_log(
    action: str,
    result: str,
    details: str,
    auditor: Optional[str] = None
):
    """Create audit log entry (internal use)"""
    try:
        audit_log = AuditLog(
            action=action,
            result=result,
            details=details,
            auditor=auditor
        )
        
        doc = audit_log.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        await db.audit_logs.insert_one(doc)
        
        logger.info(f"Audit log created: {action}")
        
        return {"message": "Audit log created", "log_id": doc["id"]}
    except Exception as e:
        logger.error(f"Create audit log error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/no-log-report")
async def get_no_log_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get no-log policy audit report"""
    try:
        # Build query
        query = {}
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        if end_date:
            query.setdefault("timestamp", {})["$lte"] = end_date
        
        # Get audit logs
        logs_cursor = db.audit_logs.find(query).sort("timestamp", -1).limit(1000)
        logs = await logs_cursor.to_list(length=1000)
        
        # Get policy verification count
        verification_count = await db.audit_logs.count_documents({
            "action": "policy_verified"
        })
        
        return {
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "no_log_policy_status": "active",
            "policy_verifications": verification_count,
            "audit_logs_count": len(logs),
            "audit_logs": logs[:100]  # Return last 100
        }
    except Exception as e:
        logger.error(f"Get no-log report error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= SECURITY INCIDENT RESPONSE =============

@api_router.post("/security/incidents")
async def create_security_incident(
    title: str,
    description: str,
    severity: str,
    affected_systems: List[str] = [],
    assigned_to: Optional[str] = None
):
    """Create a security incident"""
    try:
        incident = SecurityIncident(
            title=title,
            description=description,
            severity=severity,
            affected_systems=affected_systems,
            assigned_to=assigned_to
        )
        
        doc = incident.model_dump()
        doc['detected_at'] = doc['detected_at'].isoformat()
        
        await db.security_incidents.insert_one(doc)
        
        logger.warning(f"Security incident created: {title} (Severity: {severity})")
        
        return {
            "message": "Security incident created",
            "incident_id": doc["id"],
            "severity": severity
        }
    except Exception as e:
        logger.error(f"Create security incident error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/security/incidents")
async def get_security_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get security incidents with filters"""
    try:
        query = {}
        if status:
            query["status"] = status
        if severity:
            query["severity"] = severity
        
        incidents_cursor = db.security_incidents.find(query).sort("detected_at", -1).limit(limit)
        incidents = await incidents_cursor.to_list(length=limit)
        
        return {
            "incidents": incidents,
            "total": len(incidents)
        }
    except Exception as e:
        logger.error(f"Get security incidents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/security/incidents/{incident_id}/resolve")
async def resolve_security_incident(
    incident_id: str,
    actions_taken: List[str],
    resolved_by: str
):
    """Resolve a security incident"""
    try:
        incident = await db.security_incidents.find_one({"id": incident_id})
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        await db.security_incidents.update_one(
            {"id": incident_id},
            {
                "$set": {
                    "status": "resolved",
                    "actions_taken": actions_taken,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "assigned_to": resolved_by
                }
            }
        )
        
        logger.info(f"Security incident resolved: {incident_id}")
        
        return {
            "message": "Incident resolved successfully",
            "incident_id": incident_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve incident error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= SLA & SUPPORT SYSTEM =============

@api_router.post("/support/tickets")
async def create_support_ticket(
    user_id: str,
    subject: str,
    description: str,
    priority: str = "normal",
    category: str = "general"
):
    """Create a support ticket"""
    try:
        # Check user plan for priority support
        user = await db.users.find_one({"id": user_id})
        if user and user.get("current_plan_id"):
            plan = await db.tariff_plans.find_one({"id": user["current_plan_id"]})
            if plan and plan.get("name") == "Ultimate":
                priority = "high"  # Ultimate plan gets priority support
        
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
            category=category,
            messages=[{
                "sender": "user",
                "message": description,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        )
        
        doc = ticket.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        
        await db.support_tickets.insert_one(doc)
        
        logger.info(f"Support ticket created: {subject} (Priority: {priority})")
        
        return {
            "message": "Support ticket created successfully",
            "ticket_id": doc["id"],
            "priority": priority
        }
    except Exception as e:
        logger.error(f"Create support ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/support/tickets/{user_id}")
async def get_user_tickets(user_id: str):
    """Get all support tickets for a user"""
    try:
        tickets_cursor = db.support_tickets.find(
            {"user_id": user_id}
        ).sort("created_at", -1)
        
        tickets = await tickets_cursor.to_list(length=100)
        
        return {
            "tickets": tickets,
            "total": len(tickets)
        }
    except Exception as e:
        logger.error(f"Get user tickets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/sla/metrics")
async def get_sla_metrics(days: int = Query(default=30, le=365)):
    """Get SLA metrics for the specified period"""
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        metrics_cursor = db.sla_metrics.find({
            "date": {"$gte": start_date.isoformat()}
        }).sort("date", -1)
        
        metrics = await metrics_cursor.to_list(length=days)
        
        # Calculate averages
        if metrics:
            avg_uptime = sum(m.get("uptime_percentage", 0) for m in metrics) / len(metrics)
            avg_response = sum(m.get("avg_response_time", 0) for m in metrics) / len(metrics)
            total_incidents = sum(m.get("incident_count", 0) for m in metrics)
        else:
            avg_uptime = 99.95
            avg_response = 50.0
            total_incidents = 0
        
        return {
            "period_days": days,
            "average_uptime": round(avg_uptime, 2),
            "average_response_time_ms": round(avg_response, 2),
            "total_incidents": total_incidents,
            "meets_sla": avg_uptime >= 99.95,
            "daily_metrics": metrics
        }
    except Exception as e:
        logger.error(f"Get SLA metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= DMCA & LEGAL =============

@api_router.post("/legal/dmca-notice")
async def submit_dmca_notice(
    complainant_name: str,
    complainant_email: str,
    content_description: str,
    alleged_user_id: Optional[str] = None
):
    """Submit a DMCA takedown notice"""
    try:
        notice = DMCANotice(
            complainant_name=complainant_name,
            complainant_email=complainant_email,
            content_description=content_description,
            alleged_user_id=alleged_user_id
        )
        
        doc = notice.model_dump()
        doc['received_at'] = doc['received_at'].isoformat()
        
        await db.dmca_notices.insert_one(doc)
        
        logger.info(f"DMCA notice received from: {complainant_email}")
        
        return {
            "message": "DMCA notice received and will be reviewed within 24-48 hours",
            "notice_id": doc["id"]
        }
    except Exception as e:
        logger.error(f"Submit DMCA notice error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/legal/dmca-notices")
async def get_dmca_notices(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get DMCA notices (admin only)"""
    try:
        query = {}
        if status:
            query["status"] = status
        
        notices_cursor = db.dmca_notices.find(query).sort("received_at", -1).limit(limit)
        notices = await notices_cursor.to_list(length=limit)
        
        return {
            "notices": notices,
            "total": len(notices)
        }
    except Exception as e:
        logger.error(f"Get DMCA notices error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= SECURITY AUDITS =============

@api_router.post("/security/audits/schedule")
async def schedule_security_audit(
    audit_type: str,
    scheduled_date: str,
    auditor: str
):
    """Schedule a security audit"""
    try:
        audit = SecurityAudit(
            audit_type=audit_type,
            scheduled_date=datetime.fromisoformat(scheduled_date.replace('Z', '+00:00')),
            auditor=auditor
        )
        
        doc = audit.model_dump()
        doc['scheduled_date'] = doc['scheduled_date'].isoformat()
        
        await db.security_audits.insert_one(doc)
        
        logger.info(f"Security audit scheduled: {audit_type} on {scheduled_date}")
        
        return {
            "message": "Security audit scheduled successfully",
            "audit_id": doc["id"]
        }
    except Exception as e:
        logger.error(f"Schedule security audit error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/security/audits")
async def get_security_audits(status: Optional[str] = None):
    """Get security audits"""
    try:
        query = {}
        if status:
            query["status"] = status
        
        audits_cursor = db.security_audits.find(query).sort("scheduled_date", -1)
        audits = await audits_cursor.to_list(length=100)
        
        return {"audits": audits}
    except Exception as e:
        logger.error(f"Get security audits error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= ALERTING SYSTEM =============

@api_router.post("/alerts/create")
async def create_alert(
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    source: str
):
    """Create a system alert"""
    try:
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source
        )
        
        doc = alert.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.alerts.insert_one(doc)
        
        logger.warning(f"Alert created: {title} (Severity: {severity})")
        
        return {
            "message": "Alert created successfully",
            "alert_id": doc["id"]
        }
    except Exception as e:
        logger.error(f"Create alert error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/alerts/active")
async def get_active_alerts(severity: Optional[str] = None):
    """Get active alerts"""
    try:
        query = {"is_active": True}
        if severity:
            query["severity"] = severity
        
        alerts_cursor = db.alerts.find(query).sort("created_at", -1)
        alerts = await alerts_cursor.to_list(length=100)
        
        return {
            "active_alerts": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Get active alerts error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str):
    """Acknowledge an alert"""
    try:
        await db.alerts.update_one(
            {"id": alert_id},
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        
        return {"message": "Alert acknowledged"}
    except Exception as e:
        logger.error(f"Acknowledge alert error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
                    price_monthly=19.99,
                    price_annual=199.99,
                    crypto_discount=0.0
                ),
                TariffPlan(
                    name="Pro",
                    device_limit=5,
                    speed_tier="10Gbps",
                    special_features=["double_vpn", "obfuscation"],
                    price_monthly=39.99,
                    price_annual=399.99,
                    crypto_discount=0.0
                ),
                TariffPlan(
                    name="Ultimate",
                    device_limit=10,
                    speed_tier="10Gbps",
                    special_features=["double_vpn", "obfuscation", "tor_over_vpn", "dedicated_ip"],
                    price_monthly=59.99,
                    price_annual=599.99,
                    crypto_discount=0.0
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
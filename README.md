# AnonVPN Enterprise - Anonymous VPN Service

## 🚀 Overview
Full-featured anonymous VPN service with cryptocurrency payments, multi-protocol support, and advanced privacy features.

## ✨ Features Implemented

### Core Features
- ✅ **Crypto Payment System**: NOWPayments integration with 254+ cryptocurrencies
- ✅ **Multi-Protocol VPN**: WireGuard, OpenVPN, IKEv2, Shadowsocks
- ✅ **Advanced VPN Features**:
  - Double VPN (multi-hop routing)
  - Obfuscation (obfs4)
  - Tor-over-VPN
  - Split Tunneling
- ✅ **Tariff Plans**: Basic, Pro, Ultimate (3 plans with different features)
- ✅ **Server Network**: 55 servers across 6 regions

### Corporate Solutions
- ✅ **Organizations Management**: Multi-user corporate accounts
- ✅ **Team Members**: Role-based access (owner, admin, manager, member)
- ✅ **Security Monitoring**: Event logging and dashboard
- ✅ **Partner API**: API keys for third-party integrations
- ✅ **White-label Branding**: Custom branding for corporate clients

### New Features Added
- ✅ **Analytics Dashboard**: Comprehensive business analytics
  - Revenue tracking (daily, weekly, monthly, yearly)
  - User statistics and conversion rates
  - Geographic distribution
  - Popular plans analysis
  
- ✅ **Connection History**: User connection tracking (metadata only)
  - Session history with locations
  - Active sessions monitoring
  - Device management
  
- ✅ **Referral Program**: User growth and monetization
  - Referral code generation
  - Click and conversion tracking
  - Commission management
  
- ✅ **Dedicated IP**: Premium feature for Ultimate plan users
  - IP assignment per user
  - Location-based dedicated IPs
  
- ✅ **Shadowsocks Protocol**: Added 4th protocol for censorship bypass
  - Best for bypassing GFW (Great Firewall)
  - Full configuration generation
  - Mobile and desktop support

## 📡 API Endpoints

### Analytics & Monitoring
- `GET /api/analytics/dashboard` - Comprehensive analytics
- `GET /api/analytics/revenue?period=month` - Revenue analytics
- `GET /api/users/{user_id}/connection-history` - Connection history
- `GET /api/users/{user_id}/active-sessions` - Active VPN sessions

### Referral Program
- `POST /api/referrals/create` - Create referral code
- `GET /api/referrals/{user_id}/stats` - Referral statistics
- `POST /api/referrals/track-click` - Track referral link clicks
- `POST /api/referrals/track-signup` - Track referral signups

### Dedicated IP
- `POST /api/dedicated-ip/assign` - Assign dedicated IP (Ultimate plan)
- `GET /api/dedicated-ip/{user_id}` - Get user's dedicated IP

### Protocols
- `GET /api/protocols` - List all supported VPN protocols (4 protocols)
- `GET /api/connections/{connection_id}/config?protocol=shadowsocks` - Generate Shadowsocks config

## 🔧 Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Database**: MongoDB
- **Payment**: NOWPayments API
- **VPN Protocols**: WireGuard, OpenVPN, IKEv2, Shadowsocks

## 📊 Current Status

**MVP Level**: ~40% of full enterprise requirements
- ✅ Core VPN functionality working
- ✅ Payment system fully functional
- ✅ 4 VPN protocols supported
- ✅ Advanced privacy features
- ✅ Corporate solutions basics
- ✅ Analytics and monitoring
- ✅ Referral program

**To Production Ready**:
- ⏳ Real VPN server infrastructure deployment
- ⏳ Mobile applications (iOS/Android)
- ⏳ Desktop clients (Windows/Mac/Linux)
- ⏳ Microservices architecture
- ⏳ Kubernetes orchestration
- ⏳ Enterprise monitoring (Prometheus/Grafana)

## 🚦 Quick Start

### Backend
```bash
cd /app/backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend
```bash
cd /app/frontend
yarn install
yarn start
```

## 📝 Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=anonvpn
NOWPAYMENTS_API_KEY=your_key_here
NOWPAYMENTS_IPN_SECRET=your_secret_here
NOWPAYMENTS_SANDBOX_MODE=False
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://your-backend-url.com/api
```

## 🔐 Security Features
- No-log policy (metadata only, no traffic logs)
- End-to-end encryption
- Anonymous payments (crypto only)
- MetaMask wallet authentication
- Multiple layers of obfuscation

## 🌐 Supported Cryptocurrencies
- Bitcoin (BTC)
- Ethereum (ETH)
- Litecoin (LTC)
- Monero (XMR)
- Solana (SOL)
- USDC
- ...and 248 more via NOWPayments

## 📖 Documentation
- [API Documentation](https://invite-debug.preview.emergentagent.com/docs)
- [Payment Integration Guide](/docs/payments.md)
- [VPN Protocol Setup](/docs/vpn-setup.md)

## 🤝 Contributing
This is a private enterprise project.

## 📄 License
Proprietary - All rights reserved

---
**Status**: Active Development | **Version**: 1.0.0 | **Last Updated**: 2025

# VPN Provider Integration Guide

## Overview
AnonVPN Enterprise now supports **automated VPN server deployment** on DigitalOcean and Vultr cloud platforms.

## Features
- ✅ **Automated Server Deployment**: One-click deployment with WireGuard & OpenVPN pre-installed
- ✅ **Multi-Provider Support**: DigitalOcean and Vultr
- ✅ **Real-time Management**: List, sync, reboot, and delete servers
- ✅ **Auto-Configuration**: Servers are automatically configured with security best practices
- ✅ **Admin UI**: Web interface for easy management

## Setup

### 1. Get API Keys

#### DigitalOcean
1. Go to https://cloud.digitalocean.com/account/api/tokens
2. Click "Generate New Token"
3. Name: `AnonVPN-API`
4. Scopes: **Read & Write**
5. Copy the token

#### Vultr
1. Go to https://my.vultr.com/settings/#settingsapi
2. Click "Enable API"
3. Copy the API Key

### 2. Configure Environment Variables (Optional)

You can store API keys in environment variables:

```bash
# In backend/.env
DIGITALOCEAN_API_KEY=your_digitalocean_api_key_here
VULTR_API_KEY=your_vultr_api_key_here
```

Or provide them via the Admin UI.

## Usage

### Web UI (Recommended)

1. Navigate to `/vpn-providers` in your browser
2. Select provider (DigitalOcean or Vultr)
3. Enter API key and click "Save API Key"
4. Click "Load Regions" to see available locations
5. Click "Deploy Server" and fill in the form
6. Wait 5-10 minutes for automatic setup

### API Endpoints

#### Deploy New Server
```bash
POST /api/admin/vpn-providers/deploy-server
```

**Parameters:**
- `provider`: 'digitalocean' or 'vultr'
- `region`: Provider region code (e.g., 'nyc1', 'ewr')
- `location_name`: Display name (e.g., 'New York')
- `country_code`: Two-letter code (e.g., 'US')
- `plan`: (Optional) Server size
- `api_key`: (Optional) API key if not in env

**Example:**
```bash
curl -X POST "http://localhost:8001/api/admin/vpn-providers/deploy-server" \
  -d "provider=digitalocean" \
  -d "region=nyc1" \
  -d "location_name=New York" \
  -d "country_code=US" \
  -d "api_key=YOUR_API_KEY"
```

**Response:**
```json
{
  "message": "VPN server deployment initiated",
  "server_id": "abc-123-def",
  "provider": "digitalocean",
  "provider_server_id": "123456789",
  "location": "New York",
  "region": "nyc1",
  "status": "deploying",
  "estimated_setup_time": "5-10 minutes"
}
```

#### List Provider Servers
```bash
GET /api/admin/vpn-providers/{provider}/servers?api_key=YOUR_KEY
```

#### Get Server Info
```bash
GET /api/admin/vpn-providers/{provider}/server/{server_id}?api_key=YOUR_KEY
```

#### Sync Server Status
```bash
POST /api/admin/vpn-providers/{provider}/server/{server_id}/sync?api_key=YOUR_KEY
```

Updates database with latest info from provider (IP, status, etc.)

#### Reboot Server
```bash
POST /api/admin/vpn-providers/{provider}/server/{server_id}/reboot?api_key=YOUR_KEY
```

#### Delete Server
```bash
DELETE /api/admin/vpn-providers/{provider}/server/{server_id}?api_key=YOUR_KEY
```

⚠️ **WARNING**: This permanently deletes the server!

#### Get Available Regions
```bash
GET /api/admin/vpn-providers/{provider}/regions?api_key=YOUR_KEY
```

## Automated Setup Process

When you deploy a server, the following happens automatically:

1. **Server Creation** (1-2 minutes)
   - Cloud provider creates the VM
   - Assigns public IPv4 and IPv6 addresses

2. **WireGuard Installation** (2-3 minutes)
   - Updates system packages
   - Installs WireGuard and tools
   - Generates server keys
   - Configures firewall (UFW)
   - Enables IP forwarding

3. **OpenVPN Installation** (2-3 minutes)
   - Installs OpenVPN and Easy-RSA
   - Sets up certificate authority
   - Configures OpenVPN server

4. **Monitoring Setup** (1 minute)
   - Installs Nginx for health checks
   - Sets up Prometheus node exporter
   - Creates health endpoint at `/health.json`

5. **Activation** (Automatic)
   - Server marks as `active` in database
   - Available for user connections

## Server Plans

### DigitalOcean
- `s-1vcpu-1gb`: $6/month - 1 vCPU, 1GB RAM (Starter)
- `s-1vcpu-2gb`: $12/month - 1 vCPU, 2GB RAM (Recommended)
- `s-2vcpu-2gb`: $18/month - 2 vCPUs, 2GB RAM (High Traffic)
- `s-2vcpu-4gb`: $24/month - 2 vCPUs, 4GB RAM (Enterprise)

### Vultr
- `vc2-1c-1gb`: $6/month - 1 vCPU, 1GB RAM (Starter)
- `vc2-1c-2gb`: $12/month - 1 vCPU, 2GB RAM (Recommended)
- `vc2-2c-4gb`: $24/month - 2 vCPUs, 4GB RAM (High Traffic)

## Monitoring

### Check Server Health
```bash
curl http://YOUR_SERVER_IP/health.json
```

Response:
```json
{
  "status": "healthy",
  "hostname": "vpn-new-york-20250127",
  "timestamp": "2025-01-27T10:30:00Z",
  "services": {
    "wireguard": "active",
    "openvpn": "active"
  }
}
```

### Real-time Monitoring
Use the `/monitor` page to see live server status, load, and health.

## Troubleshooting

### Server stuck in "deploying" status
1. Wait 10 minutes for automatic setup
2. Use "Sync Status" button to refresh
3. Check server logs via provider dashboard
4. Try rebooting the server

### Cannot connect to deployed server
1. Verify server is `active` status
2. Check firewall allows ports 51820 (WireGuard) and 1194 (OpenVPN)
3. Verify IP address is correct
4. Try syncing server status

### Deployment fails
1. Check API key is valid
2. Verify account has credits/payment method
3. Check region availability
4. Review backend logs: `tail -f /var/log/supervisor/backend.err.log`

## Best Practices

1. **Start Small**: Deploy 2-3 servers initially
2. **Diverse Regions**: Choose different geographic locations
3. **Monitor Load**: Use real-time monitoring to track server capacity
4. **Scale Gradually**: Add servers as user base grows
5. **Regular Syncs**: Sync server status weekly
6. **Backup Keys**: Save server keys securely

## Cost Optimization

- Use $6/month plans for light traffic (< 50 users)
- Upgrade to $12-24/month plans for heavy traffic
- Delete unused servers to save costs
- Monitor bandwidth usage via provider dashboard

## Security Notes

- Servers are hardened with UFW firewall
- Only necessary ports are open (22, 51820, 1194)
- Automatic security updates enabled
- No-log configuration by default
- Server keys are randomly generated

## Support

For issues or questions:
- Check backend logs: `/var/log/supervisor/backend.err.log`
- Check celery logs: `/var/log/celery_worker.log`
- Review provider documentation
- Contact cloud provider support for infrastructure issues

---

**Last Updated**: January 2025
**Version**: 1.0

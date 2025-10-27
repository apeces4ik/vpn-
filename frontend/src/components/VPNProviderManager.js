import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Server, Plus, RefreshCw, Trash2, Power, MapPin,
  AlertCircle, CheckCircle, Cloud, Settings, Globe
} from 'lucide-react';
import './VPNProviderManager.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const VPNProviderManager = () => {
  const [provider, setProvider] = useState('digitalocean');
  const [apiKey, setApiKey] = useState('');
  const [servers, setServers] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDeployForm, setShowDeployForm] = useState(false);
  
  // Deploy form states
  const [selectedRegion, setSelectedRegion] = useState('');
  const [locationName, setLocationName] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [serverPlan, setServerPlan] = useState('');
  const [deploying, setDeploying] = useState(false);

  useEffect(() => {
    // Load API key from localStorage
    const savedKey = localStorage.getItem(`${provider}_api_key`);
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, [provider]);

  const saveApiKey = () => {
    if (apiKey) {
      localStorage.setItem(`${provider}_api_key`, apiKey);
      toast.success('API key saved');
      loadRegions();
    }
  };

  const loadRegions = async () => {
    if (!apiKey) {
      toast.error('Please enter API key first');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/admin/vpn-providers/${provider}/regions`,
        { params: { api_key: apiKey } }
      );
      setRegions(response.data.regions || []);
      toast.success(`Loaded ${response.data.total} regions`);
    } catch (error) {
      console.error('Failed to load regions:', error);
      toast.error('Failed to load regions. Check API key.');
    } finally {
      setLoading(false);
    }
  };

  const loadServers = async () => {
    if (!apiKey) {
      toast.error('Please enter API key first');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/admin/vpn-providers/${provider}/servers`,
        { params: { api_key: apiKey } }
      );
      setServers(response.data.servers || []);
      toast.success(`Loaded ${response.data.total} servers`);
    } catch (error) {
      console.error('Failed to load servers:', error);
      toast.error('Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  const deployServer = async () => {
    if (!selectedRegion || !locationName || !countryCode) {
      toast.error('Please fill all required fields');
      return;
    }

    setDeploying(true);
    try {
      const response = await axios.post(
        `${API}/admin/vpn-providers/deploy-server`,
        null,
        {
          params: {
            provider: provider,
            region: selectedRegion,
            location_name: locationName,
            country_code: countryCode,
            plan: serverPlan || undefined,
            api_key: apiKey
          }
        }
      );

      toast.success(
        `Server deployment initiated! Estimated setup time: ${response.data.estimated_setup_time}`,
        { duration: 5000 }
      );
      
      setShowDeployForm(false);
      setSelectedRegion('');
      setLocationName('');
      setCountryCode('');
      setServerPlan('');
      
      // Refresh server list
      setTimeout(loadServers, 2000);
    } catch (error) {
      console.error('Failed to deploy server:', error);
      toast.error(error.response?.data?.detail || 'Failed to deploy server');
    } finally {
      setDeploying(false);
    }
  };

  const syncServer = async (serverId) => {
    try {
      const response = await axios.post(
        `${API}/admin/vpn-providers/${provider}/server/${serverId}/sync`,
        null,
        { params: { api_key: apiKey } }
      );
      
      toast.success('Server status synced');
      loadServers();
    } catch (error) {
      console.error('Failed to sync server:', error);
      toast.error('Failed to sync server');
    }
  };

  const rebootServer = async (serverId) => {
    if (!window.confirm('Are you sure you want to reboot this server? It will be unavailable for 2-5 minutes.')) {
      return;
    }

    try {
      await axios.post(
        `${API}/admin/vpn-providers/${provider}/server/${serverId}/reboot`,
        null,
        { params: { api_key: apiKey } }
      );
      
      toast.success('Server reboot initiated');
      loadServers();
    } catch (error) {
      console.error('Failed to reboot server:', error);
      toast.error('Failed to reboot server');
    }
  };

  const deleteServer = async (serverId, serverName) => {
    if (!window.confirm(
      `⚠️ WARNING: This will permanently delete server "${serverName}".\n\n` +
      `This action cannot be undone and all data will be lost.\n\n` +
      `Type "DELETE" to confirm:`
    )) {
      return;
    }

    const confirmation = window.prompt('Type DELETE to confirm:');
    if (confirmation !== 'DELETE') {
      toast.error('Deletion cancelled');
      return;
    }

    try {
      await axios.delete(
        `${API}/admin/vpn-providers/${provider}/server/${serverId}`,
        { params: { api_key: apiKey } }
      );
      
      toast.success('Server deleted successfully');
      loadServers();
    } catch (error) {
      console.error('Failed to delete server:', error);
      toast.error('Failed to delete server');
    }
  };

  return (
    <div className="vpn-provider-manager">
      <div className="manager-header">
        <h1 className="manager-title">
          <Cloud size={32} />
          VPN Provider Management
        </h1>
        <p className="manager-subtitle">
          Deploy and manage VPN servers on DigitalOcean and Vultr
        </p>
      </div>

      {/* Provider Selection */}
      <div className="provider-section">
        <h2 className="section-title">
          <Settings size={24} />
          Provider Configuration
        </h2>
        
        <div className="provider-selector">
          <button
            className={`provider-btn ${provider === 'digitalocean' ? 'active' : ''}`}
            onClick={() => setProvider('digitalocean')}
          >
            <Cloud size={20} />
            DigitalOcean
          </button>
          <button
            className={`provider-btn ${provider === 'vultr' ? 'active' : ''}`}
            onClick={() => setProvider('vultr')}
          >
            <Cloud size={20} />
            Vultr
          </button>
        </div>

        <div className="api-key-input-group">
          <input
            type="password"
            placeholder={`Enter ${provider.toUpperCase()} API Key`}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="api-key-input"
          />
          <button className="btn btn-primary" onClick={saveApiKey}>
            Save API Key
          </button>
          <button className="btn btn-secondary" onClick={loadRegions}>
            <Globe size={18} />
            Load Regions
          </button>
          <button className="btn btn-secondary" onClick={loadServers}>
            <RefreshCw size={18} className={loading ? 'spinning' : ''} />
            Load Servers
          </button>
        </div>
      </div>

      {/* Deploy New Server */}
      <div className="deploy-section">
        <div className="section-header">
          <h2 className="section-title">
            <Server size={24} />
            Deploy New Server
          </h2>
          <button
            className="btn btn-primary"
            onClick={() => setShowDeployForm(!showDeployForm)}
          >
            <Plus size={18} />
            {showDeployForm ? 'Cancel' : 'Deploy Server'}
          </button>
        </div>

        {showDeployForm && (
          <div className="deploy-form">
            <div className="form-row">
              <div className="form-group">
                <label>Region *</label>
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="form-select"
                >
                  <option value="">Select region...</option>
                  {regions.map((region) => (
                    <option key={region.slug || region.id} value={region.slug || region.id}>
                      {provider === 'digitalocean' 
                        ? `${region.name} (${region.slug})`
                        : `${region.city}, ${region.country} (${region.id})`
                      }
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Location Name *</label>
                <input
                  type="text"
                  placeholder="e.g., New York"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label>Country Code *</label>
                <input
                  type="text"
                  placeholder="e.g., US"
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                  className="form-input"
                  maxLength={2}
                />
              </div>

              <div className="form-group">
                <label>Server Plan (Optional)</label>
                <input
                  type="text"
                  placeholder={provider === 'digitalocean' ? 'e.g., s-1vcpu-1gb' : 'e.g., vc2-1c-1gb'}
                  value={serverPlan}
                  onChange={(e) => setServerPlan(e.target.value)}
                  className="form-input"
                />
              </div>
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={deployServer}
              disabled={deploying}
            >
              {deploying ? (
                <>
                  <RefreshCw size={18} className="spinning" />
                  Deploying...
                </>
              ) : (
                <>
                  <Server size={18} />
                  Deploy Server
                </>
              )}
            </button>

            <div className="deploy-info">
              <AlertCircle size={16} />
              <span>
                Server will be automatically configured with WireGuard and OpenVPN.
                Setup takes approximately 5-10 minutes.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Servers List */}
      <div className="servers-list-section">
        <h2 className="section-title">
          <Server size={24} />
          Active Servers ({servers.length})
        </h2>

        {loading ? (
          <div className="loading-state">
            <RefreshCw size={48} className="spinning" />
            <p>Loading servers...</p>
          </div>
        ) : servers.length === 0 ? (
          <div className="empty-state">
            <Server size={64} />
            <p>No servers found</p>
            <p className="empty-hint">Deploy your first server to get started</p>
          </div>
        ) : (
          <div className="servers-grid">
            {servers.map((server, index) => (
              <div key={server.server_id} className="server-card-provider">
                <div className="server-card-header">
                  <div className="server-name">
                    <MapPin size={18} />
                    {server.name}
                  </div>
                  <div className={`status-badge ${server.status}`}>
                    {server.status === 'active' ? (
                      <CheckCircle size={16} />
                    ) : (
                      <AlertCircle size={16} />
                    )}
                    {server.status}
                  </div>
                </div>

                <div className="server-details">
                  <div className="detail-row">
                    <span className="detail-label">Region:</span>
                    <span className="detail-value">{server.region}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">IP Address:</span>
                    <span className="detail-value">{server.ip_address || 'Pending...'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Server ID:</span>
                    <span className="detail-value server-id">{server.server_id}</span>
                  </div>
                </div>

                <div className="server-actions-provider">
                  <button
                    className="btn-action sync"
                    onClick={() => syncServer(server.server_id)}
                    title="Sync Status"
                  >
                    <RefreshCw size={16} />
                  </button>
                  <button
                    className="btn-action reboot"
                    onClick={() => rebootServer(server.server_id)}
                    title="Reboot Server"
                  >
                    <Power size={16} />
                  </button>
                  <button
                    className="btn-action delete"
                    onClick={() => deleteServer(server.server_id, server.name)}
                    title="Delete Server"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VPNProviderManager;

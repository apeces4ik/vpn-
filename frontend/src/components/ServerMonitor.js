import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Server, Activity, AlertCircle, CheckCircle, 
  RefreshCw, Globe, Zap, Shield
} from 'lucide-react';
import './ServerMonitor.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ServerMonitor = () => {
  const [serverStatus, setServerStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchServerStatus();
    
    if (autoRefresh) {
      const interval = setInterval(fetchServerStatus, 10000); // Every 10 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchServerStatus = async () => {
    try {
      const response = await axios.get(`${API}/servers/realtime-status`);
      setServerStatus(response.data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch server status:', error);
      setLoading(false);
    }
  };

  const getHealthColor = (health) => {
    switch (health) {
      case 'healthy':
        return '#10b981';
      case 'warning':
        return '#f59e0b';
      case 'critical':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const getHealthIcon = (health) => {
    switch (health) {
      case 'healthy':
        return <CheckCircle size={20} />;
      case 'warning':
      case 'critical':
        return <AlertCircle size={20} />;
      default:
        return <Activity size={20} />;
    }
  };

  if (loading) {
    return (
      <div className="server-monitor">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading server status...</p>
        </div>
      </div>
    );
  }

  if (!serverStatus) {
    return (
      <div className="server-monitor">
        <div className="error-state">
          <AlertCircle size={48} />
          <p>Failed to load server status</p>
          <button className="btn btn-primary" onClick={fetchServerStatus}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { servers, global_stats } = serverStatus;

  return (
    <div className="server-monitor">
      {/* Header */}
      <div className="monitor-header">
        <div className="header-left">
          <h2 className="monitor-title">
            <Server size={28} />
            Server Network Status
          </h2>
          {lastUpdate && (
            <p className="last-update">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="header-actions">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-refresh</span>
          </label>
          <button 
            className="btn-refresh"
            onClick={fetchServerStatus}
            disabled={loading}
          >
            <RefreshCw size={18} className={loading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Global Stats */}
      <div className="global-stats">
        <div className="stat-card">
          <div className="stat-icon healthy">
            <CheckCircle size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{global_stats.healthy_servers}</div>
            <div className="stat-label">Healthy Servers</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon warning">
            <AlertCircle size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{global_stats.warning_servers}</div>
            <div className="stat-label">Warning Servers</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon critical">
            <AlertCircle size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{global_stats.critical_servers}</div>
            <div className="stat-label">Critical Servers</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{global_stats.total_active_connections}</div>
            <div className="stat-label">Active Connections</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Zap size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{global_stats.global_load_percent}%</div>
            <div className="stat-label">Global Load</div>
          </div>
        </div>
      </div>

      {/* Servers Grid */}
      <div className="servers-grid">
        {servers.map((server, index) => (
          <div 
            key={server.id} 
            className={`server-card-monitor ${server.health}`}
            data-testid={`server-monitor-${index}`}
          >
            <div className="server-header-monitor">
              <div className="server-location-info">
                <Globe size={18} />
                <span className="location-name">{server.location}</span>
                <span className="country-code">{server.country_code}</span>
              </div>
              <div 
                className="health-indicator"
                style={{ backgroundColor: getHealthColor(server.health) }}
                title={server.health}
              >
                {getHealthIcon(server.health)}
              </div>
            </div>

            <div className="server-hostname">{server.hostname}</div>

            <div className="load-bar-container">
              <div className="load-bar-header">
                <span>Load</span>
                <span className="load-percent">{server.load_percent}%</span>
              </div>
              <div className="load-bar">
                <div 
                  className={`load-fill ${server.health}`}
                  style={{ width: `${Math.min(server.load_percent, 100)}%` }}
                ></div>
              </div>
              <div className="load-stats">
                <span>{server.active_connections} / {server.max_capacity} connections</span>
              </div>
            </div>

            <div className="server-features-monitor">
              {server.features.double_vpn && (
                <span className="feature-badge" title="Double VPN Supported">
                  <Shield size={14} />
                  2x VPN
                </span>
              )}
              {server.features.tor && (
                <span className="feature-badge" title="Tor Supported">
                  <Shield size={14} />
                  Tor
                </span>
              )}
              {server.features.obfuscation && (
                <span className="feature-badge" title="Obfuscation Supported">
                  <Shield size={14} />
                  Obfs
                </span>
              )}
            </div>

            <div className="server-protocols">
              {server.protocols.map(protocol => (
                <span key={protocol} className="protocol-tag">
                  {protocol.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ServerMonitor;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Shield, Power, Download, ChevronRight, Globe, 
  Zap, Activity, Clock, ArrowUpRight, MapPin, Settings,
  Award, Wifi, Users, LifeBuoy, Server
} from 'lucide-react';
import './Dashboard.css';
import AdvancedFeaturesModal from '../components/AdvancedFeaturesModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user, logout }) => {
  const navigate = useNavigate();
  const [servers, setServers] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentConnection, setCurrentConnection] = useState(null);
  const [connectionHistory, setConnectionHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userPlan, setUserPlan] = useState(null);
  const [showAdvancedModal, setShowAdvancedModal] = useState(false);
  const [advancedServer, setAdvancedServer] = useState(null);

  useEffect(() => {
    fetchData();
    // Fetch connection history every 30 seconds
    const interval = setInterval(() => {
      fetchConnectionHistory();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [serversRes, locationsRes] = await Promise.all([
        axios.get(`${API}/servers`),
        axios.get(`${API}/servers/locations`)
      ]);
      
      setServers(serversRes.data);
      setLocations(locationsRes.data);

      // Fetch user plan if they have one
      if (user.current_plan_id) {
        const planRes = await axios.get(`${API}/tariffs`);
        const plan = planRes.data.find(p => p.id === user.current_plan_id);
        setUserPlan(plan);
      }

      // Fetch connection history
      await fetchConnectionHistory();

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setLoading(false);
    }
  };

  const fetchConnectionHistory = async () => {
    try {
      const response = await axios.get(`${API}/connections/user/${user.id}`, {
        params: { active_only: false }
      });
      setConnectionHistory(response.data.slice(0, 10)); // Last 10 connections
    } catch (error) {
      console.error('Failed to fetch connection history:', error);
    }
  };

  const handleConnect = async (server) => {
    try {
      const response = await axios.post(`${API}/connections/connect`, null, {
        params: {
          user_id: user.id,
          server_id: server.id,
          device_name: 'Web Browser'
        }
      });

      setCurrentConnection(response.data);
      setIsConnected(true);
      setSelectedServer(server);
    } catch (error) {
      console.error('Failed to connect:', error);
      if (error.response?.status === 403) {
        navigate('/payment');
      }
    }
  };

  const handleDisconnect = async () => {
    if (!currentConnection) return;

    try {
      await axios.post(`${API}/connections/${currentConnection.id}/disconnect`);
      setIsConnected(false);
      setCurrentConnection(null);
      setSelectedServer(null);
    } catch (error) {
      console.error('Failed to disconnect:', error);
    }
  };

  const handleDownloadConfig = async (server, protocol = 'wireguard') => {
    try {
      const response = await axios.post(`${API}/connections/connect`, null, {
        params: {
          user_id: user.id,
          server_id: server.id,
          device_name: 'Config Download',
          protocol: protocol
        }
      });

      const configUrl = `${API}/connections/${response.data.id}/config?protocol=${protocol}`;
      window.open(configUrl, '_blank');
      toast.success(`${protocol.toUpperCase()} config downloaded`);
    } catch (error) {
      console.error('Failed to download config:', error);
      if (error.response?.status === 403) {
        navigate('/payment');
      }
    }
  };

  const handleAdvancedConnect = (server) => {
    setAdvancedServer(server);
    setShowAdvancedModal(true);
  };

  const handleAdvancedConnectionCreated = async (connection) => {
    setCurrentConnection(connection);
    setIsConnected(true);
    setSelectedServer(advancedServer);
    
    // Download the advanced config
    try {
      const configUrl = `${API}/connections/${connection.id}/advanced-config`;
      window.open(configUrl, '_blank');
      toast.success('Advanced connection created! Config downloaded.');
    } catch (error) {
      console.error('Failed to download advanced config:', error);
      toast.error('Connection created but config download failed');
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="dashboard" data-testid="dashboard">
      <nav className="dashboard-nav" data-testid="dashboard-nav">
        <div className="nav-container">
          <div className="logo">
            <Shield size={28} />
            <span className="logo-text">AnonVPN</span>
          </div>
          <div className="nav-actions">
            {user.wallet_address && (
              <div className="wallet-badge" title={user.wallet_address}>
                <div className="wallet-icon">🔐</div>
                <span className="wallet-address">
                  {user.wallet_address.slice(0, 6)}...{user.wallet_address.slice(-4)}
                </span>
              </div>
            )}
            {!userPlan && (
              <button 
                className="btn btn-primary"
                onClick={() => navigate('/payment')}
                data-testid="upgrade-btn"
              >
                Upgrade Now
              </button>
            )}
            <button 
              className="btn btn-secondary"
              onClick={() => {
                logout();
                navigate('/');
              }}
              data-testid="logout-btn"
              style={{ marginLeft: '10px' }}
            >
              Disconnect
            </button>
          </div>
        </div>
      </nav>

      <div className="dashboard-container">
        {/* Quick Connect VPN Banner */}
        <div className="quick-connect-banner" onClick={() => navigate('/quick-connect')} 
             style={{
               background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
               padding: '1.5rem 2rem',
               borderRadius: '15px',
               marginBottom: '1.5rem',
               cursor: 'pointer',
               boxShadow: '0 10px 30px rgba(102, 126, 234, 0.3)',
               transition: 'all 0.3s ease',
               display: 'flex',
               alignItems: 'center',
               justifyContent: 'space-between'
             }}
             onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
             onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'white' }}>
            <div style={{ 
              background: 'rgba(255, 255, 255, 0.2)', 
              padding: '1rem', 
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Zap size={32} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '700' }}>
                🚀 Быстрое подключение VPN
              </h3>
              <p style={{ margin: '0.25rem 0 0 0', opacity: 0.9 }}>
                Подключайтесь к бесплатным VPN серверам одним кликом - IP адрес меняется реально!
              </p>
            </div>
          </div>
          <ArrowUpRight size={32} color="white" />
        </div>

        {/* Connection Status */}
        <div className="connection-status-card" data-testid="connection-status">
          <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-icon">
              <Power size={48} />
            </div>
            <div className="status-content">
              <div className="status-label">
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>
              {isConnected && selectedServer && (
                <div className="status-location" data-testid="connected-location">
                  <MapPin size={16} />
                  {selectedServer.location}, {selectedServer.country_code}
                </div>
              )}
            </div>
          </div>

          {isConnected ? (
            <button 
              className="btn btn-disconnect"
              onClick={handleDisconnect}
              data-testid="disconnect-btn"
            >
              Disconnect
            </button>
          ) : (
            <div className="connection-hint">
              Select a server below to connect
            </div>
          )}
        </div>

        {/* User Info & Plan */}
        <div className="info-cards-grid">
          <div className="info-card" data-testid="user-info-card">
            <div className="info-card-header">
              <Activity size={20} />
              <span>Account Status</span>
            </div>
            <div className="info-card-content">
              <div className="info-row">
                <span>Plan:</span>
                <strong>{userPlan ? userPlan.name : 'Free Trial'}</strong>
              </div>
              <div className="info-row">
                <span>Anonymous ID:</span>
                <strong className="user-id">{user.anonymous_id.substring(0, 16)}...</strong>
              </div>
              {!userPlan && (
                <button 
                  className="btn btn-primary btn-sm mt-3"
                  onClick={() => navigate('/payment')}
                  data-testid="select-plan-btn"
                >
                  Select a Plan
                  <ChevronRight size={16} />
                </button>
              )}
            </div>
          </div>

          <div className="info-card" data-testid="stats-card">
            <div className="info-card-header">
              <Zap size={20} />
              <span>Quick Stats</span>
            </div>
            <div className="info-card-content">
              <div className="stat-item">
                <Globe size={24} className="stat-icon" />
                <div>
                  <div className="stat-value">{locations.length}</div>
                  <div className="stat-label">Locations</div>
                </div>
              </div>
              <div className="stat-item">
                <Activity size={24} className="stat-icon" />
                <div>
                  <div className="stat-value">{servers.length}</div>
                  <div className="stat-label">Servers</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Links Menu */}
        <div className="quick-links-section" style={{
          background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
          borderRadius: '20px',
          padding: '28px',
          marginBottom: '32px',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
        }}>
          <h3 style={{
            color: 'white',
            fontSize: '20px',
            fontWeight: '700',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <Settings size={24} style={{ color: '#8B5CF6' }} />
            Quick Access
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '16px'
          }}>
            <button
              onClick={() => navigate('/history')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '16px 20px',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(79, 70, 229, 0.1) 100%)',
                border: '2px solid rgba(99, 102, 241, 0.4)',
                borderRadius: '12px',
                color: 'white',
                cursor: 'pointer',
                transition: 'all 0.3s',
                fontSize: '15px',
                fontWeight: '600'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(79, 70, 229, 0.2) 100%)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(99, 102, 241, 0.3)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(79, 70, 229, 0.1) 100%)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <Wifi size={20} style={{ color: '#818CF8' }} />
              <span>Connection History</span>
            </button>

            <button
              onClick={() => navigate('/referral')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '16px 20px',
                background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.2) 0%, rgba(219, 39, 119, 0.1) 100%)',
                border: '2px solid rgba(236, 72, 153, 0.4)',
                borderRadius: '12px',
                color: 'white',
                cursor: 'pointer',
                transition: 'all 0.3s',
                fontSize: '15px',
                fontWeight: '600'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(236, 72, 153, 0.3) 0%, rgba(219, 39, 119, 0.2) 100%)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(236, 72, 153, 0.3)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(236, 72, 153, 0.2) 0%, rgba(219, 39, 119, 0.1) 100%)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <Users size={20} style={{ color: '#F472B6' }} />
              <span>Refer & Earn</span>
            </button>

            <button
              onClick={() => navigate('/support')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '16px 20px',
                background: 'linear-gradient(135deg, rgba(251, 146, 60, 0.2) 0%, rgba(249, 115, 22, 0.1) 100%)',
                border: '2px solid rgba(251, 146, 60, 0.4)',
                borderRadius: '12px',
                color: 'white',
                cursor: 'pointer',
                transition: 'all 0.3s',
                fontSize: '15px',
                fontWeight: '600'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(251, 146, 60, 0.3) 0%, rgba(249, 115, 22, 0.2) 100%)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(251, 146, 60, 0.3)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, rgba(251, 146, 60, 0.2) 0%, rgba(249, 115, 22, 0.1) 100%)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <LifeBuoy size={20} style={{ color: '#FB923C' }} />
              <span>Get Support</span>
            </button>
          </div>
        </div>

        {/* Servers List */}
        <div className="servers-section" data-testid="servers-section">
          <div className="section-header">
            <h2 className="section-title">Available Servers</h2>
            <div className="server-count">{servers.length} servers online</div>
          </div>

          <div className="servers-grid">
            {servers.map((server, index) => (
              <div 
                className={`server-card ${selectedServer?.id === server.id ? 'selected' : ''}`}
                key={server.id}
                data-testid={`server-card-${index}`}
              >
                <div className="server-header">
                  <div className="server-flag">
                    {server.country_code}
                  </div>
                  <div className="server-info">
                    <div className="server-location">{server.location}</div>
                    <div className="server-hostname">{server.hostname}</div>
                  </div>
                </div>

                <div className="server-stats">
                  <div className="server-stat">
                    <Activity size={16} />
                    <span>{server.current_connections}/{server.max_capacity}</span>
                  </div>
                  <div className="server-stat">
                    <Zap size={16} />
                    <span>10 Gbps</span>
                  </div>
                </div>

                <div className="server-actions">
                  {isConnected && selectedServer?.id === server.id ? (
                    <button 
                      className="btn btn-secondary btn-sm btn-block"
                      onClick={handleDisconnect}
                      data-testid={`disconnect-server-btn-${index}`}
                    >
                      Disconnect
                    </button>
                  ) : (
                    <>
                      <button 
                        className="btn btn-primary btn-sm"
                        onClick={() => handleConnect(server)}
                        disabled={isConnected}
                        data-testid={`connect-btn-${index}`}
                      >
                        <Power size={16} />
                        Connect
                      </button>
                      <button 
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleDownloadConfig(server)}
                        data-testid={`download-config-btn-${index}`}
                      >
                        <Download size={16} />
                      </button>
                      {userPlan && (
                        <button 
                          className="btn btn-accent btn-sm"
                          onClick={() => handleAdvancedConnect(server)}
                          data-testid={`advanced-btn-${index}`}
                          title="Advanced Features"
                        >
                          <Settings size={16} />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Connection History */}
        {connectionHistory.length > 0 && (
          <div className="history-section" data-testid="connection-history">
            <div className="section-header">
              <h2 className="section-title">Connection History</h2>
              <div className="history-count">Last {connectionHistory.length} connections</div>
            </div>

            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Server</th>
                    <th>Device</th>
                    <th>Connected At</th>
                    <th>Duration</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {connectionHistory.map((conn, index) => {
                    const server = servers.find(s => s.id === conn.server_id);
                    const connectedAt = new Date(conn.connected_at);
                    const disconnectedAt = conn.disconnected_at ? new Date(conn.disconnected_at) : null;
                    const duration = disconnectedAt 
                      ? Math.floor((disconnectedAt - connectedAt) / 60000) 
                      : Math.floor((new Date() - connectedAt) / 60000);
                    
                    return (
                      <tr key={index}>
                        <td>{server ? `${server.location}, ${server.country_code}` : 'Unknown'}</td>
                        <td>{conn.device_name}</td>
                        <td>{connectedAt.toLocaleString()}</td>
                        <td>{duration} min</td>
                        <td>
                          <span className={`status-badge-small ${conn.is_active ? 'active' : 'inactive'}`}>
                            {conn.is_active ? 'Active' : 'Disconnected'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Advanced Features Modal */}
      <AdvancedFeaturesModal
        isOpen={showAdvancedModal}
        onClose={() => setShowAdvancedModal(false)}
        server={advancedServer}
        user={user}
        userPlan={userPlan}
        onConnectionCreated={handleAdvancedConnectionCreated}
      />
    </div>
  );
};

export default Dashboard;

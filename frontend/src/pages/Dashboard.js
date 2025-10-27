import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Shield, Power, Download, ChevronRight, Globe, 
  Zap, Activity, Clock, ArrowUpRight, MapPin
} from 'lucide-react';
import './Dashboard.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user }) => {
  const navigate = useNavigate();
  const [servers, setServers] = useState([]);
  const [locations, setLocations] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentConnection, setCurrentConnection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userPlan, setUserPlan] = useState(null);

  useEffect(() => {
    fetchData();
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

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setLoading(false);
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

  const handleDownloadConfig = async (server) => {
    try {
      const response = await axios.post(`${API}/connections/connect`, null, {
        params: {
          user_id: user.id,
          server_id: server.id,
          device_name: 'Config Download'
        }
      });

      const configUrl = `${API}/connections/${response.data.id}/config`;
      window.open(configUrl, '_blank');
    } catch (error) {
      console.error('Failed to download config:', error);
      if (error.response?.status === 403) {
        navigate('/payment');
      }
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
            {!userPlan && (
              <button 
                className="btn btn-primary"
                onClick={() => navigate('/payment')}
                data-testid="upgrade-btn"
              >
                Upgrade Now
              </button>
            )}
          </div>
        </div>
      </nav>

      <div className="dashboard-container">
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
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

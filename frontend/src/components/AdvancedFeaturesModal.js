import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  X, Shield, Eye, Network, Split, Plus, Trash2, 
  Info, Check, AlertCircle, Globe
} from 'lucide-react';
import './AdvancedFeaturesModal.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdvancedFeaturesModal = ({ 
  isOpen, 
  onClose, 
  server, 
  user,
  userPlan,
  onConnectionCreated 
}) => {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // Advanced feature states
  const [protocol, setProtocol] = useState('wireguard');
  const [enableDoubleVPN, setEnableDoubleVPN] = useState(false);
  const [exitServer, setExitServer] = useState(null);
  const [exitServers, setExitServers] = useState([]);
  const [enableObfuscation, setEnableObfuscation] = useState(false);
  const [enableTor, setEnableTor] = useState(false);
  const [torServers, setTorServers] = useState([]);
  const [splitTunnelRules, setSplitTunnelRules] = useState([]);
  const [newRule, setNewRule] = useState({ type: 'domain', value: '', action: 'bypass' });

  useEffect(() => {
    if (isOpen) {
      fetchAdvancedFeatures();
    }
  }, [isOpen]);

  useEffect(() => {
    if (enableDoubleVPN && exitServers.length === 0) {
      fetchExitServers();
    }
  }, [enableDoubleVPN]);

  useEffect(() => {
    if (enableTor && torServers.length === 0) {
      fetchTorServers();
    }
  }, [enableTor]);

  const fetchAdvancedFeatures = async () => {
    try {
      const response = await axios.get(`${API}/features/advanced`);
      setFeatures(response.data.features || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch advanced features:', error);
      setLoading(false);
    }
  };

  const fetchExitServers = async () => {
    try {
      const response = await axios.get(`${API}/servers/double-vpn`);
      const pairs = response.data.server_pairs || [];
      // Find pairs where entry server is our selected server
      const available = pairs
        .filter(pair => pair.entry_server.id === server.id)
        .map(pair => pair.exit_server);
      setExitServers(available);
    } catch (error) {
      console.error('Failed to fetch exit servers:', error);
    }
  };

  const fetchTorServers = async () => {
    try {
      const response = await axios.get(`${API}/servers/tor-enabled`);
      setTorServers(response.data.servers || []);
    } catch (error) {
      console.error('Failed to fetch Tor servers:', error);
    }
  };

  const addSplitTunnelRule = () => {
    if (!newRule.value) {
      toast.error('Please enter a value for the rule');
      return;
    }

    setSplitTunnelRules([...splitTunnelRules, { ...newRule }]);
    setNewRule({ type: 'domain', value: '', action: 'bypass' });
    toast.success('Rule added');
  };

  const removeSplitTunnelRule = (index) => {
    setSplitTunnelRules(splitTunnelRules.filter((_, i) => i !== index));
    toast.success('Rule removed');
  };

  const createAdvancedConnection = async () => {
    setCreating(true);
    try {
      // Validate requirements
      if (enableDoubleVPN && !exitServer) {
        toast.error('Please select an exit server for Double VPN');
        setCreating(false);
        return;
      }

      if (enableTor && !torServers.find(s => s.id === server.id)) {
        toast.error('Selected server does not support Tor. Please choose a Tor-enabled server.');
        setCreating(false);
        return;
      }

      const params = {
        user_id: user.id,
        server_id: server.id,
        protocol: protocol,
        device_name: 'Web Browser - Advanced',
        enable_double_vpn: enableDoubleVPN,
        enable_obfuscation: enableObfuscation,
        enable_tor: enableTor
      };

      if (enableDoubleVPN && exitServer) {
        params.exit_server_id = exitServer.id;
      }

      if (splitTunnelRules.length > 0) {
        params.split_tunnel_rules = JSON.stringify(splitTunnelRules);
      }

      const response = await axios.post(`${API}/connections/advanced`, null, {
        params: params
      });

      toast.success('Advanced connection created successfully!');
      onConnectionCreated(response.data);
      onClose();
    } catch (error) {
      console.error('Failed to create advanced connection:', error);
      
      let errorMessage = 'Failed to create connection';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      toast.error(errorMessage, { duration: 5000 });
    } finally {
      setCreating(false);
    }
  };

  const getFeatureAvailable = (featureId) => {
    if (!userPlan) return false;
    
    const planLevels = { 'Basic': 1, 'Pro': 2, 'Ultimate': 3 };
    const userLevel = planLevels[userPlan.name] || 0;
    
    switch (featureId) {
      case 'double_vpn':
      case 'obfuscation':
        return userLevel >= 2; // Pro or Ultimate
      case 'tor_over_vpn':
        return userLevel >= 3; // Ultimate only
      case 'split_tunneling':
        return true; // Available for all
      default:
        return false;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content advanced-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 className="modal-title">
              <Shield size={24} />
              Advanced Connection Setup
            </h2>
            <p className="modal-subtitle">
              Configure advanced VPN features for {server.location}
            </p>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading-spinner">
              <div className="spinner"></div>
            </div>
          ) : (
            <>
              {/* Protocol Selection */}
              <div className="config-section">
                <h3 className="config-title">
                  <Globe size={20} />
                  VPN Protocol
                </h3>
                <div className="protocol-grid">
                  {['wireguard', 'openvpn', 'ikev2'].map(p => (
                    <button
                      key={p}
                      className={`protocol-option ${protocol === p ? 'selected' : ''}`}
                      onClick={() => setProtocol(p)}
                    >
                      {p === 'wireguard' && <Check size={16} />}
                      <span className="protocol-name">
                        {p === 'wireguard' ? 'WireGuard' : p === 'openvpn' ? 'OpenVPN' : 'IKEv2'}
                      </span>
                      {p === 'wireguard' && <span className="recommended-badge">Recommended</span>}
                    </button>
                  ))}
                </div>
              </div>

              {/* Advanced Features */}
              <div className="config-section">
                <h3 className="config-title">
                  <Shield size={20} />
                  Advanced Features
                </h3>

                {/* Double VPN */}
                <div className="feature-option">
                  <div className="feature-header">
                    <label className="feature-checkbox">
                      <input
                        type="checkbox"
                        checked={enableDoubleVPN}
                        onChange={(e) => setEnableDoubleVPN(e.target.checked)}
                        disabled={!getFeatureAvailable('double_vpn')}
                      />
                      <span className="checkmark"></span>
                      <div className="feature-info">
                        <span className="feature-name">
                          <Network size={18} />
                          Double VPN (Multi-Hop)
                        </span>
                        <span className="feature-description">
                          Route traffic through two VPN servers for extra security
                        </span>
                      </div>
                    </label>
                    {!getFeatureAvailable('double_vpn') && (
                      <span className="feature-badge pro">Pro</span>
                    )}
                  </div>

                  {enableDoubleVPN && (
                    <div className="feature-config">
                      <label className="config-label">Exit Server:</label>
                      <select
                        className="config-select"
                        value={exitServer?.id || ''}
                        onChange={(e) => {
                          const server = exitServers.find(s => s.id === e.target.value);
                          setExitServer(server);
                        }}
                      >
                        <option value="">Select exit server...</option>
                        {exitServers.map(s => (
                          <option key={s.id} value={s.id}>
                            {s.location}, {s.country_code}
                          </option>
                        ))}
                      </select>
                      <div className="config-hint">
                        <Info size={14} />
                        Your traffic: Device → {server.location} → {exitServer?.location || '...'} → Internet
                      </div>
                    </div>
                  )}
                </div>

                {/* Obfuscation */}
                <div className="feature-option">
                  <div className="feature-header">
                    <label className="feature-checkbox">
                      <input
                        type="checkbox"
                        checked={enableObfuscation}
                        onChange={(e) => setEnableObfuscation(e.target.checked)}
                        disabled={!getFeatureAvailable('obfuscation') || protocol === 'ikev2'}
                      />
                      <span className="checkmark"></span>
                      <div className="feature-info">
                        <span className="feature-name">
                          <Eye size={18} />
                          Obfuscation (obfs4)
                        </span>
                        <span className="feature-description">
                          Disguise VPN traffic to bypass firewalls and DPI
                        </span>
                      </div>
                    </label>
                    {!getFeatureAvailable('obfuscation') && (
                      <span className="feature-badge pro">Pro</span>
                    )}
                  </div>
                  {protocol === 'ikev2' && enableObfuscation && (
                    <div className="config-warning">
                      <AlertCircle size={14} />
                      Obfuscation requires OpenVPN protocol
                    </div>
                  )}
                </div>

                {/* Tor over VPN */}
                <div className="feature-option">
                  <div className="feature-header">
                    <label className="feature-checkbox">
                      <input
                        type="checkbox"
                        checked={enableTor}
                        onChange={(e) => setEnableTor(e.target.checked)}
                        disabled={!getFeatureAvailable('tor_over_vpn')}
                      />
                      <span className="checkmark"></span>
                      <div className="feature-info">
                        <span className="feature-name">
                          <Shield size={18} />
                          Tor over VPN
                        </span>
                        <span className="feature-description">
                          Maximum anonymity: VPN + Tor network routing
                        </span>
                      </div>
                    </label>
                    {!getFeatureAvailable('tor_over_vpn') && (
                      <span className="feature-badge ultimate">Ultimate</span>
                    )}
                  </div>
                  {enableTor && !torServers.find(s => s.id === server.id) && (
                    <div className="config-warning">
                      <AlertCircle size={14} />
                      Selected server does not support Tor. Available Tor servers: {torServers.length}
                    </div>
                  )}
                </div>

                {/* Split Tunneling */}
                <div className="feature-option">
                  <div className="feature-header">
                    <label className="feature-checkbox">
                      <input
                        type="checkbox"
                        checked={splitTunnelRules.length > 0}
                        onChange={(e) => {
                          if (!e.target.checked) {
                            setSplitTunnelRules([]);
                          }
                        }}
                      />
                      <span className="checkmark"></span>
                      <div className="feature-info">
                        <span className="feature-name">
                          <Split size={18} />
                          Split Tunneling
                        </span>
                        <span className="feature-description">
                          Route specific apps/sites outside VPN tunnel
                        </span>
                      </div>
                    </label>
                  </div>

                  <div className="feature-config">
                    {/* Add Rule Form */}
                    <div className="split-tunnel-form">
                      <select
                        className="rule-type-select"
                        value={newRule.type}
                        onChange={(e) => setNewRule({ ...newRule, type: e.target.value })}
                      >
                        <option value="domain">Domain</option>
                        <option value="ip">IP Address</option>
                        <option value="subnet">Subnet</option>
                      </select>
                      <input
                        type="text"
                        className="rule-value-input"
                        placeholder={
                          newRule.type === 'domain' ? 'example.com' :
                          newRule.type === 'ip' ? '8.8.8.8' :
                          '192.168.1.0/24'
                        }
                        value={newRule.value}
                        onChange={(e) => setNewRule({ ...newRule, value: e.target.value })}
                      />
                      <select
                        className="rule-action-select"
                        value={newRule.action}
                        onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                      >
                        <option value="bypass">Bypass VPN</option>
                        <option value="include">Use VPN</option>
                      </select>
                      <button className="btn-add-rule" onClick={addSplitTunnelRule}>
                        <Plus size={18} />
                      </button>
                    </div>

                    {/* Rules List */}
                    {splitTunnelRules.length > 0 && (
                      <div className="rules-list">
                        {splitTunnelRules.map((rule, index) => (
                          <div key={index} className="rule-item">
                            <div className="rule-details">
                              <span className="rule-type">{rule.type}</span>
                              <span className="rule-value">{rule.value}</span>
                              <span className={`rule-action ${rule.action}`}>
                                {rule.action === 'bypass' ? '→ Direct' : '→ VPN'}
                              </span>
                            </div>
                            <button
                              className="btn-remove-rule"
                              onClick={() => removeSplitTunnelRule(index)}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={createAdvancedConnection}
            disabled={creating || loading}
          >
            {creating ? (
              <>
                <div className="spinner-sm"></div>
                Creating...
              </>
            ) : (
              <>
                <Shield size={18} />
                Create Connection
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdvancedFeaturesModal;

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './QuickConnect.css';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const QuickConnect = ({ user }) => {
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectionDetails, setConnectionDetails] = useState(null);
  const [currentIP, setCurrentIP] = useState(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchServers();
    checkConnectionStatus();
    fetchCurrentIP();
  }, []);

  const fetchServers = async () => {
    try {
      setLoading(true);
      // Fetch VPNGate servers (free servers)
      const response = await axios.get(`${API}/api/servers`);
      const freeServers = response.data.filter(s => s.is_free && s.is_active);
      
      if (freeServers.length === 0) {
        // If no free servers, fetch from VPNGate
        await axios.post(`${API}/api/servers/vpngate/refresh-free`);
        const refreshed = await axios.get(`${API}/api/servers`);
        setServers(refreshed.data.filter(s => s.is_free && s.is_active));
      } else {
        setServers(freeServers);
      }
      
      // Auto-select first server
      if (freeServers.length > 0) {
        setSelectedServer(freeServers[0]);
      }
    } catch (error) {
      console.error('Error fetching servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkConnectionStatus = async () => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/api/proxy/status/${user.id}`);
      if (response.data.status === 'connected') {
        setIsConnected(true);
        setConnectionDetails(response.data);
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const fetchCurrentIP = async () => {
    try {
      const response = await axios.get(`${API}/api/proxy/test`);
      setCurrentIP(response.data.your_ip);
    } catch (error) {
      console.error('Error fetching IP:', error);
    }
  };

  const handleQuickConnect = async () => {
    if (!selectedServer || !user) {
      alert('Пожалуйста, выберите сервер и войдите в систему');
      return;
    }

    try {
      setConnecting(true);
      const response = await axios.post(
        `${API}/api/proxy/quick-connect?user_id=${user.id}&server_id=${selectedServer.id}`
      );

      setIsConnected(true);
      setConnectionDetails(response.data);
      setShowInstructions(true);
      
      // Refresh IP after connection
      setTimeout(fetchCurrentIP, 2000);
      
      alert('✅ VPN подключен! Настройте прокси в браузере согласно инструкциям.');
    } catch (error) {
      console.error('Connection error:', error);
      alert(`Ошибка подключения: ${error.response?.data?.detail || error.message}`);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!user) return;

    try {
      await axios.post(`${API}/api/proxy/disconnect?user_id=${user.id}`);
      setIsConnected(false);
      setConnectionDetails(null);
      setShowInstructions(false);
      fetchCurrentIP();
      alert('VPN отключен');
    } catch (error) {
      console.error('Disconnect error:', error);
      alert(`Ошибка отключения: ${error.message}`);
    }
  };

  const downloadPACFile = () => {
    if (!connectionDetails) return;
    const pacUrl = `${API}${connectionDetails.connection.pac_url}`;
    window.open(pacUrl, '_blank');
  };

  if (loading) {
    return (
      <div className="quick-connect-container">
        <div className="loading-spinner">Загрузка серверов...</div>
      </div>
    );
  }

  return (
    <div className="quick-connect-container">
      <div className="quick-connect-header">
        <h2>🚀 Быстрое подключение VPN</h2>
        <p className="subtitle">Бесплатные VPN серверы от VPNGate</p>
      </div>

      <div className="ip-display">
        <div className="ip-label">Ваш текущий IP адрес:</div>
        <div className="ip-address">{currentIP || 'Загрузка...'}</div>
        <button onClick={fetchCurrentIP} className="refresh-ip-btn">
          🔄 Обновить
        </button>
      </div>

      <div className="connection-status">
        <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          <span className="status-text">
            {isConnected ? '🟢 Подключено' : '🔴 Отключено'}
          </span>
        </div>
      </div>

      {!isConnected && (
        <div className="server-selection">
          <label className="server-label">Выберите сервер:</label>
          <select
            className="server-select"
            value={selectedServer?.id || ''}
            onChange={(e) => {
              const server = servers.find(s => s.id === e.target.value);
              setSelectedServer(server);
            }}
          >
            {servers.map(server => (
              <option key={server.id} value={server.id}>
                {server.location} ({server.country_code}) - {server.provider}
              </option>
            ))}
          </select>

          {selectedServer && (
            <div className="server-info">
              <p><strong>Локация:</strong> {selectedServer.location}</p>
              <p><strong>IP:</strong> {selectedServer.ipv4_address}</p>
              <p><strong>Протоколы:</strong> {selectedServer.protocols.join(', ')}</p>
            </div>
          )}
        </div>
      )}

      <div className="action-buttons">
        {!isConnected ? (
          <button
            onClick={handleQuickConnect}
            disabled={connecting || !selectedServer}
            className="connect-btn"
          >
            {connecting ? '⏳ Подключение...' : '🔌 ПОДКЛЮЧИТЬСЯ'}
          </button>
        ) : (
          <button onClick={handleDisconnect} className="disconnect-btn">
            ⛔ ОТКЛЮЧИТЬСЯ
          </button>
        )}
      </div>

      {isConnected && connectionDetails && (
        <div className="connection-details">
          <h3>📋 Настройки прокси</h3>
          
          <div className="proxy-config">
            <div className="config-item">
              <span className="config-label">Тип прокси:</span>
              <span className="config-value">SOCKS5</span>
            </div>
            <div className="config-item">
              <span className="config-label">Хост:</span>
              <span className="config-value">{connectionDetails.connection.proxy_host}</span>
            </div>
            <div className="config-item">
              <span className="config-label">Порт:</span>
              <span className="config-value">{connectionDetails.connection.proxy_port}</span>
            </div>
            <div className="config-item">
              <span className="config-label">Сервер:</span>
              <span className="config-value">{connectionDetails.server.location} ({connectionDetails.server.country_code})</span>
            </div>
          </div>

          <button onClick={() => setShowInstructions(!showInstructions)} className="toggle-instructions-btn">
            {showInstructions ? '▼ Скрыть инструкции' : '▶ Показать инструкции по настройке'}
          </button>

          {showInstructions && (
            <div className="instructions-panel">
              <h4>🔧 Настройка прокси в браузере</h4>
              
              <div className="browser-instructions">
                <div className="browser-section">
                  <h5>Google Chrome / Edge:</h5>
                  <ol>
                    <li>Откройте Настройки → Система → Прокси-сервер</li>
                    <li>Включите "Использовать прокси-сервер"</li>
                    <li>Введите адрес: <code>{connectionDetails.connection.proxy_host}:{connectionDetails.connection.proxy_port}</code></li>
                    <li>Сохраните и перезапустите браузер</li>
                  </ol>
                </div>

                <div className="browser-section">
                  <h5>Mozilla Firefox:</h5>
                  <ol>
                    <li>Откройте Настройки → Основные → Параметры сети</li>
                    <li>Выберите "Ручная настройка прокси"</li>
                    <li>SOCKS Host: <code>{connectionDetails.connection.proxy_host}</code></li>
                    <li>Port: <code>{connectionDetails.connection.proxy_port}</code></li>
                    <li>Выберите "SOCKS v5"</li>
                    <li>Включите "Проксировать DNS при использовании SOCKS v5"</li>
                    <li>Нажмите OK</li>
                  </ol>
                </div>
              </div>

              <div className="pac-file-section">
                <h5>Автоматическая настройка (PAC файл):</h5>
                <button onClick={downloadPACFile} className="download-pac-btn">
                  📥 Скачать PAC файл
                </button>
                <p className="pac-note">
                  Используйте PAC файл для автоматической настройки прокси в браузере
                </p>
              </div>

              <div className="important-note">
                <h5>⚠️ Важно:</h5>
                <ul>
                  <li>После настройки прокси обновите страницу и проверьте ваш IP адрес выше</li>
                  <li>IP адрес должен измениться на IP сервера VPN</li>
                  <li>Для отключения VPN - отключите прокси в настройках браузера или нажмите "Отключиться"</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="vpngate-attribution">
        <p>
          <small>
            🌐 Серверы предоставлены <a href="https://www.vpngate.net" target="_blank" rel="noopener noreferrer">VPN Gate</a> - 
            бесплатный академический проект университета Цукуба, Япония
          </small>
        </p>
      </div>
    </div>
  );
};

export default QuickConnect;

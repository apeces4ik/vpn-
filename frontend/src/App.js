import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster, toast } from 'sonner';
import './App.css';

import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import PaymentPage from './pages/PaymentPage';
import AdminPanel from './pages/AdminPanel';
import TeamDashboard from './pages/TeamDashboard';
import ServerMonitor from './components/ServerMonitor';
import VPNProviderManager from './components/VPNProviderManager';
// New UI Pages
import DeviceManagement from './pages/DeviceManagement';
import LoyaltyProgram from './pages/LoyaltyProgram';
import CustomDNS from './pages/CustomDNS';
import ConnectionHistory from './pages/ConnectionHistory';
import ReferralProgram from './pages/ReferralProgram';
import AffiliateDashboard from './pages/AffiliateDashboard';
import SupportTickets from './pages/SupportTickets';
import WhiteLabelBranding from './pages/WhiteLabelBranding';
import WhiteLabelConfig from './pages/WhiteLabelConfig';
import ServerMonitoringDashboard from './pages/ServerMonitoringDashboard';
import SecurityDashboard from './pages/SecurityDashboard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing user in localStorage
    const savedUser = localStorage.getItem('anonvpn_user');
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setUser(userData);
      } catch (e) {
        console.error('Failed to parse user data');
      }
    }
    setLoading(false);
  }, []);

  const createUser = async (walletAddress = null, isWalletLogin = false) => {
    try {
      const requestData = isWalletLogin ? { wallet_address: walletAddress } : { email: walletAddress };
      
      const response = await axios.post(`${API}/users`, requestData);
      const userData = response.data;
      localStorage.setItem('anonvpn_user', JSON.stringify(userData));
      setUser(userData);
      toast.success('Welcome to AnonVPN!');
      return userData;
    } catch (error) {
      console.error('Failed to create user:', error);
      toast.error('Failed to create account');
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('anonvpn_user');
    setUser(null);
    toast.success('Logged out successfully');
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="App">
      <Toaster position="top-right" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage user={user} createUser={createUser} />} />
          <Route 
            path="/dashboard" 
            element={
              user ? <Dashboard user={user} logout={logout} /> : <Navigate to="/" replace />
            } 
          />
          <Route 
            path="/payment" 
            element={
              user ? <PaymentPage user={user} setUser={setUser} logout={logout} /> : <Navigate to="/" replace />
            } 
          />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/team" element={<TeamDashboard />} />
          <Route path="/monitor" element={<ServerMonitor />} />
          <Route path="/vpn-providers" element={<VPNProviderManager />} />
          
          {/* New UI Routes */}
          <Route 
            path="/devices" 
            element={user ? <DeviceManagement user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/loyalty" 
            element={user ? <LoyaltyProgram user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/dns" 
            element={user ? <CustomDNS user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/history" 
            element={user ? <ConnectionHistory user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/referral" 
            element={user ? <ReferralProgram user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/affiliate" 
            element={user ? <AffiliateDashboard user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/support" 
            element={user ? <SupportTickets user={user} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/branding" 
            element={user ? <WhiteLabelBranding user={user} organizationId={user.organization_id} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/whitelabel" 
            element={<WhiteLabelConfig />} 
          />
          <Route 
            path="/monitoring" 
            element={<ServerMonitoringDashboard />} 
          />
          <Route 
            path="/security" 
            element={user ? <SecurityDashboard user={user} organizationId={user.organization_id} /> : <Navigate to="/" replace />} 
          />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;

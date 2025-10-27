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

  const createUser = async (email = null) => {
    try {
      const response = await axios.post(`${API}/users`, null, {
        params: { email }
      });
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
              user ? <Dashboard user={user} /> : <Navigate to="/" replace />
            } 
          />
          <Route 
            path="/payment" 
            element={
              user ? <PaymentPage user={user} setUser={setUser} /> : <Navigate to="/" replace />
            } 
          />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/team" element={<TeamDashboard />} />
          <Route path="/monitor" element={<ServerMonitor />} />
          <Route path="/vpn-providers" element={<VPNProviderManager />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;

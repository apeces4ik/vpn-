import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Shield, Users, Server, DollarSign, Activity, 
  TrendingUp, Globe, BarChart3, PieChart
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, PieChart as RePieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './AdminPanel.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPanel = () => {
  const [dashboard, setDashboard] = useState(null);
  const [geography, setGeography] = useState(null);
  const [connections, setConnections] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [dashboardRes, geographyRes, connectionsRes, usersRes] = await Promise.all([
        axios.get(`${API}/admin/analytics/dashboard`),
        axios.get(`${API}/admin/analytics/geography`),
        axios.get(`${API}/admin/analytics/connections-history?days=7`),
        axios.get(`${API}/admin/users?limit=10`)
      ]);
      
      setDashboard(dashboardRes.data);
      setGeography(geographyRes.data);
      setConnections(connectionsRes.data);
      setUsers(usersRes.data.users);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
      setLoading(false);
    }
  };

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  const regionData = geography?.regions ? Object.entries(geography.regions).map(([name, value]) => ({ name, value })) : [];
  const connectionData = connections?.daily_connections ? Object.entries(connections.daily_connections).map(([date, count]) => ({ date, count })) : [];

  return (
    <div className="admin-panel" data-testid="admin-panel">
      <nav className="admin-nav">
        <div className="nav-container">
          <div className="logo">
            <Shield size={28} />
            <span className="logo-text">AnonVPN Admin</span>
          </div>
        </div>
      </nav>

      <div className="admin-container">
        <h1 className="admin-title">Analytics Dashboard</h1>

        {/* KPI Cards */}
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-icon users">
              <Users size={32} />
            </div>
            <div className="kpi-content">
              <div className="kpi-value">{dashboard?.users?.total || 0}</div>
              <div className="kpi-label">Total Users</div>
              <div className="kpi-sub">{dashboard?.users?.with_plans || 0} with active plans</div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon servers">
              <Server size={32} />
            </div>
            <div className="kpi-content">
              <div className="kpi-value">{dashboard?.servers?.total || 0}</div>
              <div className="kpi-label">Active Servers</div>
              <div className="kpi-sub">{dashboard?.servers?.total_connections || 0} active connections</div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon revenue">
              <DollarSign size={32} />
            </div>
            <div className="kpi-content">
              <div className="kpi-value">${dashboard?.revenue?.total?.toFixed(2) || 0}</div>
              <div className="kpi-label">Total Revenue</div>
              <div className="kpi-sub">{dashboard?.revenue?.total_payments || 0} payments</div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-icon utilization">
              <Activity size={32} />
            </div>
            <div className="kpi-content">
              <div className="kpi-value">{dashboard?.servers?.utilization?.toFixed(1) || 0}%</div>
              <div className="kpi-label">Server Utilization</div>
              <div className="kpi-sub">Capacity: {dashboard?.servers?.total_capacity || 0}</div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="charts-grid">
          <div className="chart-card">
            <div className="chart-header">
              <BarChart3 size={20} />
              <h3>Connections Last 7 Days</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={connectionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d2d30" />
                <XAxis dataKey="date" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip 
                  contentStyle={{ background: '#1a1a1c', border: '1px solid #2d2d30' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <Globe size={20} />
              <h3>Server Distribution by Region</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <RePieChart>
                <Pie
                  data={regionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {regionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: '#1a1a1c', border: '1px solid #2d2d30' }}
                />
              </RePieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Users */}
        <div className="table-card">
          <div className="table-header">
            <h3>Recent Users</h3>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Anonymous ID</th>
                  <th>Email</th>
                  <th>Plan</th>
                  <th>Created At</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user, index) => (
                  <tr key={index}>
                    <td className="mono">{user.anonymous_id?.substring(0, 16)}...</td>
                    <td>{user.email || 'Anonymous'}</td>
                    <td>{user.current_plan_id ? 'Active' : 'Free Trial'}</td>
                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                    <td>
                      <span className={`status-badge ${user.current_plan_id ? 'active' : 'trial'}`}>
                        {user.current_plan_id ? 'Paid' : 'Trial'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;

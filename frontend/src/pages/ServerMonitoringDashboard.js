import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Activity, Server, Cpu, HardDrive, Users, 
  TrendingUp, Loader, AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ServerMonitoringDashboard = () => {
  const [overview, setOverview] = useState(null);
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [serverMetrics, setServerMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchData();
    }, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [overviewRes, serversRes] = await Promise.all([
        axios.get(`${API}/servers/metrics/overview`),
        axios.get(`${API}/servers`)
      ]);
      setOverview(overviewRes.data);
      setServers(serversRes.data.slice(0, 20)); // First 20 servers
      if (serversRes.data.length > 0 && !selectedServer) {
        setSelectedServer(serversRes.data[0].id);
        fetchServerMetrics(serversRes.data[0].id);
      }
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load monitoring data');
      setLoading(false);
    }
  };

  const fetchServerMetrics = async (serverId) => {
    try {
      const response = await axios.get(`${API}/servers/${serverId}/metrics`, {
        params: { period: '24h' }
      });
      setServerMetrics(response.data.metrics || []);
    } catch (error) {
      console.error('Failed to fetch server metrics:', error);
    }
  };

  const handleServerSelect = (serverId) => {
    setSelectedServer(serverId);
    fetchServerMetrics(serverId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const chartData = serverMetrics.map(m => ({
    time: new Date(m.timestamp).toLocaleTimeString(),
    cpu: m.cpu_usage,
    memory: m.memory_usage,
    connections: m.active_connections
  }));

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-cyan-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Server Monitoring</h1>
          <p className="text-gray-400">Real-time server performance metrics</p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <Card className="bg-gradient-to-br from-blue-900/50 to-cyan-900/50 border-blue-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-300 text-sm mb-1">Total Servers</p>
                  <p className="text-3xl font-bold text-white">
                    {overview?.total_servers || 0}
                  </p>
                </div>
                <Server className="w-10 h-10 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Active Connections</p>
                  <p className="text-3xl font-bold text-green-400">
                    {overview?.total_connections || 0}
                  </p>
                </div>
                <Users className="w-10 h-10 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Avg CPU Usage</p>
                  <p className="text-3xl font-bold text-yellow-400">
                    {(overview?.average_cpu || 0).toFixed(1)}%
                  </p>
                </div>
                <Cpu className="w-10 h-10 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Network Load</p>
                  <p className="text-3xl font-bold text-purple-400">
                    {(overview?.network_usage_percent || 0).toFixed(1)}%
                  </p>
                </div>
                <Activity className="w-10 h-10 text-purple-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white">CPU & Memory Usage</CardTitle>
              <CardDescription className="text-gray-400">Last 24 hours</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  />
                  <Line type="monotone" dataKey="cpu" stroke="#F59E0B" strokeWidth={2} />
                  <Line type="monotone" dataKey="memory" stroke="#8B5CF6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white">Active Connections</CardTitle>
              <CardDescription className="text-gray-400">Last 24 hours</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  />
                  <Area type="monotone" dataKey="connections" stroke="#10B981" fill="#10B98130" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Server List */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Server Status</CardTitle>
            <CardDescription className="text-gray-400">
              Real-time server health and performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {servers.map((server) => {
                const isHealthy = server.status === 'active' && (server.load || 0) < 80;
                return (
                  <div 
                    key={server.id}
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      selectedServer === server.id 
                        ? 'border-blue-500 bg-blue-900/20' 
                        : 'border-gray-700 bg-gray-800/30 hover:border-gray-600'
                    }`}
                    onClick={() => handleServerSelect(server.id)}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${
                          isHealthy ? 'bg-green-500' : 'bg-red-500'
                        } animate-pulse`} />
                        <div>
                          <div className="text-white font-semibold">{server.location}</div>
                          <div className="text-gray-400 text-sm">{server.ip_address}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={isHealthy ? 'bg-green-600' : 'bg-red-600'}>
                          {server.status}
                        </Badge>
                        <div className="text-right">
                          <div className="text-gray-400 text-xs">Load</div>
                          <div className="text-white font-semibold">{(server.load || 0).toFixed(1)}%</div>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <div className="text-gray-400 text-xs mb-1">Connections</div>
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-blue-400" />
                          <span className="text-white">{server.current_connections || 0}</span>
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs mb-1">Capacity</div>
                        <Progress value={(server.current_connections / server.capacity) * 100} className="h-2" />
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs mb-1">Region</div>
                        <div className="text-white text-sm">{server.region}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ServerMonitoringDashboard;
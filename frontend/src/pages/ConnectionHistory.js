import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  History, Activity, MapPin, Clock, Wifi, WifiOff,
  XCircle, Loader, Calendar, TrendingUp, ArrowLeft
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ConnectionHistory = ({ user }) => {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [activeSessions, setActiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [disconnectingSession, setDisconnectingSession] = useState(null);
  const [showDisconnectDialog, setShowDisconnectDialog] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchActiveSessions();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      await Promise.all([
        fetchHistory(),
        fetchActiveSessions()
      ]);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch connection data:', error);
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/connection-history`);
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
      toast.error('Failed to load connection history');
    }
  };

  const fetchActiveSessions = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/active-sessions`);
      setActiveSessions(response.data.sessions || []);
    } catch (error) {
      console.error('Failed to fetch active sessions:', error);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectingSession) return;

    try {
      await axios.delete(`${API}/users/${user.id}/sessions/${disconnectingSession}/disconnect`);
      toast.success('Session disconnected successfully');
      fetchActiveSessions();
    } catch (error) {
      console.error('Failed to disconnect session:', error);
      toast.error(error.response?.data?.detail || 'Failed to disconnect session');
    } finally {
      setShowDisconnectDialog(false);
      setDisconnectingSession(null);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900 to-gray-900">
        <Loader className="w-12 h-12 animate-spin text-indigo-400" />
      </div>
    );
  }

  const totalDataUsed = history.reduce((sum, h) => sum + (h.data_used || 0), 0);
  const totalDuration = history.reduce((sum, h) => sum + (h.duration || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900 to-purple-900">
      <div className="border-b border-gray-700/50 bg-gray-900/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group"
          >
            <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
            <span className="font-medium">Back to Dashboard</span>
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-3 bg-indigo-500/20 rounded-xl">
              <History className="w-8 h-8 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Connection History</h1>
              <p className="text-gray-400 mt-1">Track your VPN usage and manage active sessions</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-200 text-sm font-medium mb-1">Active Now</p>
                  <p className="text-4xl font-bold text-white">{activeSessions.length}</p>
                </div>
                <div className="p-4 bg-green-500/30 rounded-2xl">
                  <Activity className="w-8 h-8 text-green-300 animate-pulse" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border-blue-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-200 text-sm font-medium mb-1">Total Sessions</p>
                  <p className="text-4xl font-bold text-white">{history.length}</p>
                </div>
                <div className="p-4 bg-blue-500/30 rounded-2xl">
                  <History className="w-8 h-8 text-blue-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-200 text-sm font-medium mb-1">Data Used</p>
                  <p className="text-3xl font-bold text-white">{formatBytes(totalDataUsed)}</p>
                </div>
                <div className="p-4 bg-purple-500/30 rounded-2xl">
                  <TrendingUp className="w-8 h-8 text-purple-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-yellow-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-yellow-200 text-sm font-medium mb-1">Total Time</p>
                  <p className="text-3xl font-bold text-white">{formatDuration(totalDuration)}</p>
                </div>
                <div className="p-4 bg-yellow-500/30 rounded-2xl">
                  <Clock className="w-8 h-8 text-yellow-300" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="sessions" className="space-y-6">
          <TabsList className="bg-gray-800/80 backdrop-blur-xl border border-gray-700/50 p-1.5 h-auto">
            <TabsTrigger 
              value="sessions" 
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-green-600 data-[state=active]:to-emerald-600 data-[state=active]:text-white px-6 py-3 rounded-lg font-semibold"
            >
              <Wifi className="w-4 h-4 mr-2" />
              Active Sessions
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-indigo-600 data-[state=active]:to-purple-600 data-[state=active]:text-white px-6 py-3 rounded-lg font-semibold"
            >
              <History className="w-4 h-4 mr-2" />
              History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="sessions">
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-white text-2xl">Active VPN Sessions</CardTitle>
                <CardDescription className="text-gray-400 text-base">
                  Currently connected devices • Updates every 10 seconds
                </CardDescription>
              </CardHeader>
              <CardContent>
                {activeSessions.length === 0 ? (
                  <div className="text-center py-16">
                    <div className="inline-flex p-6 bg-gray-700/50 rounded-full mb-6">
                      <WifiOff className="w-16 h-16 text-gray-500" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-3">No Active Sessions</h3>
                    <p className="text-gray-400 text-lg">Connect to a VPN server to see active sessions here</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {activeSessions.map((session) => (
                      <div 
                        key={session.id}
                        className="p-6 rounded-xl border-2 border-green-500/40 bg-gradient-to-r from-green-900/30 to-emerald-900/20 backdrop-blur-xl hover:border-green-500/60 transition-all"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-4">
                              <Badge className="bg-green-500 text-white px-3 py-1 font-semibold">
                                <Activity className="w-4 h-4 mr-1.5 animate-pulse" />
                                LIVE
                              </Badge>
                              <span className="text-white font-bold text-lg">{session.device_name}</span>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                              <div>
                                <div className="text-gray-400 text-sm mb-1 font-medium">Server</div>
                                <div className="text-white flex items-center gap-2 font-semibold">
                                  <MapPin className="w-4 h-4 text-green-400" />
                                  {session.server_location}
                                </div>
                              </div>
                              <div>
                                <div className="text-gray-400 text-sm mb-1 font-medium">IP Address</div>
                                <div className="text-white font-mono">{session.ip_address || 'N/A'}</div>
                              </div>
                              <div>
                                <div className="text-gray-400 text-sm mb-1 font-medium">Duration</div>
                                <div className="text-white font-semibold">{formatDuration(session.duration)}</div>
                              </div>
                              <div>
                                <div className="text-gray-400 text-sm mb-1 font-medium">Data</div>
                                <div className="text-white font-semibold">{formatBytes(session.data_used)}</div>
                              </div>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setDisconnectingSession(session.id);
                              setShowDisconnectDialog(true);
                            }}
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/20 font-semibold ml-4"
                          >
                            <XCircle className="w-5 h-5 mr-2" />
                            Disconnect
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history">
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-white text-2xl">Past Connections</CardTitle>
                <CardDescription className="text-gray-400 text-base">
                  Connection metadata only • No browsing activity logged
                </CardDescription>
              </CardHeader>
              <CardContent>
                {history.length === 0 ? (
                  <div className="text-center py-16">
                    <div className="inline-flex p-6 bg-gray-700/50 rounded-full mb-6">
                      <History className="w-16 h-16 text-gray-500" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-3">No History Yet</h3>
                    <p className="text-gray-400 text-lg">Your connection history will appear here</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-700">
                        <TableHead className="text-gray-400 font-semibold">Date & Time</TableHead>
                        <TableHead className="text-gray-400 font-semibold">Server</TableHead>
                        <TableHead className="text-gray-400 font-semibold">Device</TableHead>
                        <TableHead className="text-gray-400 font-semibold">Duration</TableHead>
                        <TableHead className="text-gray-400 font-semibold">Data</TableHead>
                        <TableHead className="text-gray-400 font-semibold">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.map((item) => (
                        <TableRow key={item.id} className="border-gray-700/50 hover:bg-gray-700/30">
                          <TableCell className="text-gray-300">
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4" />
                              {new Date(item.connected_at).toLocaleString()}
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-300">
                            <div className="flex items-center gap-2">
                              <MapPin className="w-4 h-4 text-indigo-400" />
                              {item.server_location}
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-300">{item.device_name}</TableCell>
                          <TableCell className="text-gray-300 font-mono">{formatDuration(item.duration)}</TableCell>
                          <TableCell className="text-gray-300 font-mono">{formatBytes(item.data_used)}</TableCell>
                          <TableCell>
                            <Badge className={item.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-gray-600/20 text-gray-300'}>
                              {item.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <AlertDialog open={showDisconnectDialog} onOpenChange={setShowDisconnectDialog}>
          <AlertDialogContent className="bg-gray-900 border-gray-700 backdrop-blur-xl">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-2xl font-bold text-white">Disconnect Session?</AlertDialogTitle>
              <AlertDialogDescription className="text-gray-400 text-base">
                This will force disconnect the VPN session. The device will need to reconnect manually.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-gray-800 text-white hover:bg-gray-700 border-gray-700">Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDisconnect} className="bg-gradient-to-r from-red-600 to-red-700">Disconnect</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
};

export default ConnectionHistory;
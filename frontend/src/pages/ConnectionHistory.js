import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  History, Activity, MapPin, Clock, Wifi, WifiOff,
  XCircle, Loader, Calendar, Globe
} from 'lucide-react';
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
  const [history, setHistory] = useState([]);
  const [activeSessions, setActiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [disconnectingSession, setDisconnectingSession] = useState(null);
  const [showDisconnectDialog, setShowDisconnectDialog] = useState(false);

  useEffect(() => {
    fetchData();
    // Refresh active sessions every 10 seconds
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
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Connection History</h1>
          <p className="text-gray-400">View your VPN usage and active sessions</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Active Sessions</p>
                  <p className="text-2xl font-bold text-white">{activeSessions.length}</p>
                </div>
                <Activity className="w-8 h-8 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Connections</p>
                  <p className="text-2xl font-bold text-white">{history.length}</p>
                </div>
                <History className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Data Used</p>
                  <p className="text-2xl font-bold text-white">
                    {formatBytes(history.reduce((sum, h) => sum + (h.data_used || 0), 0))}
                  </p>
                </div>
                <Globe className="w-8 h-8 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Duration</p>
                  <p className="text-2xl font-bold text-white">
                    {formatDuration(history.reduce((sum, h) => sum + (h.duration || 0), 0))}
                  </p>
                </div>
                <Clock className="w-8 h-8 text-yellow-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="sessions" className="space-y-4">
          <TabsList className="bg-gray-800 border-gray-700">
            <TabsTrigger value="sessions" className="data-[state=active]:bg-blue-600">
              <Wifi className="w-4 h-4 mr-2" />
              Active Sessions
            </TabsTrigger>
            <TabsTrigger value="history" className="data-[state=active]:bg-blue-600">
              <History className="w-4 h-4 mr-2" />
              Connection History
            </TabsTrigger>
          </TabsList>

          {/* Active Sessions Tab */}
          <TabsContent value="sessions">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Active VPN Sessions</CardTitle>
                <CardDescription className="text-gray-400">
                  Currently connected devices
                </CardDescription>
              </CardHeader>
              <CardContent>
                {activeSessions.length === 0 ? (
                  <div className="text-center py-12">
                    <WifiOff className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-xl font-semibold text-white mb-2">No Active Sessions</h3>
                    <p className="text-gray-400">Connect to a VPN server to see active sessions</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {activeSessions.map((session) => (
                      <div 
                        key={session.id}
                        className="p-4 rounded-lg border border-green-500/30 bg-green-900/20"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge className="bg-green-600">
                                <Activity className="w-3 h-3 mr-1" />
                                Active
                              </Badge>
                              <span className="text-white font-semibold">{session.device_name}</span>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <div className="text-gray-400">Server</div>
                                <div className="text-white flex items-center gap-1">
                                  <MapPin className="w-3 h-3" />
                                  {session.server_location}
                                </div>
                              </div>
                              <div>
                                <div className="text-gray-400">IP Address</div>
                                <div className="text-white">{session.ip_address || 'N/A'}</div>
                              </div>
                              <div>
                                <div className="text-gray-400">Duration</div>
                                <div className="text-white">{formatDuration(session.duration)}</div>
                              </div>
                              <div>
                                <div className="text-gray-400">Data Used</div>
                                <div className="text-white">{formatBytes(session.data_used)}</div>
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
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                          >
                            <XCircle className="w-4 h-4 mr-1" />
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

          {/* History Tab */}
          <TabsContent value="history">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Connection History</CardTitle>
                <CardDescription className="text-gray-400">
                  Past VPN connections (no logs of browsing activity)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {history.length === 0 ? (
                  <div className="text-center py-12">
                    <History className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-xl font-semibold text-white mb-2">No History</h3>
                    <p className="text-gray-400">Your connection history will appear here</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-700">
                        <TableHead className="text-gray-400">Date</TableHead>
                        <TableHead className="text-gray-400">Server</TableHead>
                        <TableHead className="text-gray-400">Device</TableHead>
                        <TableHead className="text-gray-400">Duration</TableHead>
                        <TableHead className="text-gray-400">Data Used</TableHead>
                        <TableHead className="text-gray-400">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.map((item) => (
                        <TableRow key={item.id} className="border-gray-700">
                          <TableCell className="text-gray-300">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {new Date(item.connected_at).toLocaleString()}
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-300">
                            <div className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {item.server_location}
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-300">{item.device_name}</TableCell>
                          <TableCell className="text-gray-300">{formatDuration(item.duration)}</TableCell>
                          <TableCell className="text-gray-300">{formatBytes(item.data_used)}</TableCell>
                          <TableCell>
                            <Badge variant={item.status === 'completed' ? 'default' : 'secondary'}>
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

        {/* Disconnect Confirmation Dialog */}
        <AlertDialog open={showDisconnectDialog} onOpenChange={setShowDisconnectDialog}>
          <AlertDialogContent className="bg-gray-800 text-white border-gray-700">
            <AlertDialogHeader>
              <AlertDialogTitle>Disconnect Session?</AlertDialogTitle>
              <AlertDialogDescription className="text-gray-400">
                This will force disconnect the VPN session. The device will need to reconnect manually.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-gray-700 text-white hover:bg-gray-600">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction 
                onClick={handleDisconnect}
                className="bg-red-600 hover:bg-red-700"
              >
                Disconnect
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
};

export default ConnectionHistory;

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Smartphone, Monitor, Tablet, Trash2, Plus, Shield, 
  CheckCircle, XCircle, Loader, ArrowLeft, Zap, Activity
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Badge } from '../components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DeviceManagement = ({ user }) => {
  const navigate = useNavigate();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addingDevice, setAddingDevice] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [newDevice, setNewDevice] = useState({
    device_name: '',
    device_type: 'desktop'
  });

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await axios.get(`${API}/users/${user.id}/devices`);
      setDevices(response.data.devices || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      toast.error('Failed to load devices');
      setLoading(false);
    }
  };

  const handleAddDevice = async () => {
    if (!newDevice.device_name.trim()) {
      toast.error('Please enter device name');
      return;
    }

    setAddingDevice(true);
    try {
      await axios.post(`${API}/users/${user.id}/devices`, {
        device_name: newDevice.device_name,
        device_type: newDevice.device_type
      });
      toast.success('Device added successfully');
      setNewDevice({ device_name: '', device_type: 'desktop' });
      setOpenDialog(false);
      fetchDevices();
    } catch (error) {
      console.error('Failed to add device:', error);
      toast.error(error.response?.data?.detail || 'Failed to add device');
    } finally {
      setAddingDevice(false);
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    try {
      await axios.delete(`${API}/users/${user.id}/devices/${deviceId}`);
      toast.success('Device removed successfully');
      fetchDevices();
    } catch (error) {
      console.error('Failed to delete device:', error);
      toast.error('Failed to remove device');
    }
  };

  const getDeviceIcon = (type) => {
    switch (type) {
      case 'mobile':
        return <Smartphone className="w-6 h-6" />;
      case 'tablet':
        return <Tablet className="w-6 h-6" />;
      default:
        return <Monitor className="w-6 h-6" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <Loader className="w-12 h-12 animate-spin text-blue-400" />
      </div>
    );
  }

  const activeDevices = devices.filter(d => d.status === 'active').length;
  const deviceLimit = user.device_limit || 5;
  const availableSlots = deviceLimit - devices.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header with Back Button */}
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
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-3 bg-blue-500/20 rounded-xl">
              <Smartphone className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Device Management</h1>
              <p className="text-gray-400 mt-1">Manage all your connected devices in one place</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border-blue-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-200 text-sm font-medium mb-1">Active Devices</p>
                  <p className="text-4xl font-bold text-white">{activeDevices}</p>
                </div>
                <div className="p-4 bg-blue-500/30 rounded-2xl">
                  <Activity className="w-8 h-8 text-blue-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-200 text-sm font-medium mb-1">Device Limit</p>
                  <p className="text-4xl font-bold text-white">{devices.length}/{deviceLimit}</p>
                </div>
                <div className="p-4 bg-purple-500/30 rounded-2xl">
                  <Shield className="w-8 h-8 text-purple-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-200 text-sm font-medium mb-1">Available Slots</p>
                  <p className="text-4xl font-bold text-white">{availableSlots}</p>
                </div>
                <div className="p-4 bg-green-500/30 rounded-2xl">
                  <Zap className="w-8 h-8 text-green-300" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Add Device Button */}
        <div className="mb-8">
          <Dialog open={openDialog} onOpenChange={setOpenDialog}>
            <DialogTrigger asChild>
              <Button 
                className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold px-6 py-6 text-base shadow-lg shadow-blue-500/30 transition-all hover:scale-105"
                disabled={devices.length >= deviceLimit}
              >
                <Plus className="w-5 h-5 mr-2" />
                Add New Device
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-gray-900 border-gray-700 backdrop-blur-xl">
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold text-white">Add New Device</DialogTitle>
                <DialogDescription className="text-gray-400">
                  Register a new device to use with AnonVPN
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-5 mt-6">
                <div>
                  <Label htmlFor="device-name" className="text-white font-medium">Device Name</Label>
                  <Input
                    id="device-name"
                    placeholder="My iPhone 15 Pro"
                    value={newDevice.device_name}
                    onChange={(e) => setNewDevice({...newDevice, device_name: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white mt-2 h-12"
                  />
                </div>
                <div>
                  <Label htmlFor="device-type" className="text-white font-medium">Device Type</Label>
                  <Select 
                    value={newDevice.device_type}
                    onValueChange={(value) => setNewDevice({...newDevice, device_type: value})}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-600 text-white mt-2 h-12">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-600">
                      <SelectItem value="desktop" className="text-white">🖥️ Desktop</SelectItem>
                      <SelectItem value="mobile" className="text-white">📱 Mobile</SelectItem>
                      <SelectItem value="tablet" className="text-white">📱 Tablet</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button 
                  onClick={handleAddDevice} 
                  disabled={addingDevice}
                  className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 h-12 text-base font-semibold mt-6"
                >
                  {addingDevice ? (
                    <>
                      <Loader className="w-5 h-5 mr-2 animate-spin" />
                      Adding Device...
                    </>
                  ) : (
                    <>
                      <Plus className="w-5 h-5 mr-2" />
                      Add Device
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Devices Grid */}
        {devices.length === 0 ? (
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
            <CardContent className="p-16 text-center">
              <div className="inline-flex p-6 bg-blue-500/20 rounded-full mb-6">
                <Shield className="w-16 h-16 text-blue-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">No Devices Yet</h3>
              <p className="text-gray-400 mb-6 text-lg">Add your first device to get started with AnonVPN</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {devices.map((device) => (
              <Card 
                key={device.id} 
                className="bg-gray-800/50 border-gray-700 backdrop-blur-xl hover:border-blue-500/50 transition-all duration-300 group hover:scale-105 hover:shadow-xl hover:shadow-blue-500/20"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="p-3 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl group-hover:scale-110 transition-transform">
                        <div className="text-blue-400">
                          {getDeviceIcon(device.device_type)}
                        </div>
                      </div>
                      <div>
                        <CardTitle className="text-white text-xl font-bold">{device.device_name}</CardTitle>
                        <CardDescription className="text-gray-400 capitalize text-sm mt-1">
                          {device.device_type}
                        </CardDescription>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteDevice(device.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/20 transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400 font-medium">Status</span>
                      <Badge 
                        className={
                          device.status === 'active' 
                            ? 'bg-green-500/20 text-green-300 border-green-500/50 px-3 py-1' 
                            : 'bg-gray-600/20 text-gray-300 border-gray-600/50 px-3 py-1'
                        }
                      >
                        {device.status === 'active' ? (
                          <><CheckCircle className="w-3 h-3 mr-1.5 inline" />Active</>
                        ) : (
                          <><XCircle className="w-3 h-3 mr-1.5 inline" />Inactive</>
                        )}
                      </Badge>
                    </div>
                    <div className="pt-4 border-t border-gray-700">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Added</span>
                        <span className="text-gray-300 font-medium">
                          {new Date(device.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {device.last_active && (
                        <div className="flex items-center justify-between text-sm mt-2">
                          <span className="text-gray-500">Last Active</span>
                          <span className="text-gray-300 font-medium">
                            {new Date(device.last_active).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DeviceManagement;
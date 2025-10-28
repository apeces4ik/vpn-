import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Smartphone, Monitor, Tablet, Trash2, Plus, Shield, 
  CheckCircle, XCircle, Loader
} from 'lucide-react';
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
        return <Smartphone className="w-5 h-5" />;
      case 'tablet':
        return <Tablet className="w-5 h-5" />;
      default:
        return <Monitor className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Device Management</h1>
          <p className="text-gray-400">Manage your connected devices</p>
        </div>

        {/* Stats Card */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <div className="text-gray-400 text-sm mb-1">Active Devices</div>
                <div className="text-3xl font-bold text-white">
                  {devices.filter(d => d.status === 'active').length}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm mb-1">Device Limit</div>
                <div className="text-3xl font-bold text-white">
                  {devices.length} / {user.device_limit || 5}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm mb-1">Available Slots</div>
                <div className="text-3xl font-bold text-green-400">
                  {(user.device_limit || 5) - devices.length}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Add Device Button */}
        <div className="mb-6">
          <Dialog open={openDialog} onOpenChange={setOpenDialog}>
            <DialogTrigger asChild>
              <Button 
                className="bg-blue-600 hover:bg-blue-700"
                disabled={devices.length >= (user.device_limit || 5)}
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Device
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-gray-800 text-white border-gray-700">
              <DialogHeader>
                <DialogTitle>Add New Device</DialogTitle>
                <DialogDescription className="text-gray-400">
                  Register a new device to use with AnonVPN
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label htmlFor="device-name">Device Name</Label>
                  <Input
                    id="device-name"
                    placeholder="My iPhone"
                    value={newDevice.device_name}
                    onChange={(e) => setNewDevice({...newDevice, device_name: e.target.value})}
                    className="bg-gray-700 border-gray-600 text-white"
                  />
                </div>
                <div>
                  <Label htmlFor="device-type">Device Type</Label>
                  <Select 
                    value={newDevice.device_type}
                    onValueChange={(value) => setNewDevice({...newDevice, device_type: value})}
                  >
                    <SelectTrigger className="bg-gray-700 border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-700 border-gray-600 text-white">
                      <SelectItem value="desktop">Desktop</SelectItem>
                      <SelectItem value="mobile">Mobile</SelectItem>
                      <SelectItem value="tablet">Tablet</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button 
                  onClick={handleAddDevice} 
                  disabled={addingDevice}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {addingDevice ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Add Device
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Devices Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {devices.length === 0 ? (
            <Card className="col-span-full bg-gray-800/50 border-gray-700">
              <CardContent className="p-12 text-center">
                <Shield className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-semibold text-white mb-2">No Devices</h3>
                <p className="text-gray-400">Add your first device to get started</p>
              </CardContent>
            </Card>
          ) : (
            devices.map((device) => (
              <Card key={device.id} className="bg-gray-800/50 border-gray-700 hover:border-blue-500 transition-all">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-blue-600/20 rounded-lg text-blue-400">
                        {getDeviceIcon(device.device_type)}
                      </div>
                      <div>
                        <CardTitle className="text-white text-lg">{device.device_name}</CardTitle>
                        <CardDescription className="text-gray-400 capitalize">
                          {device.device_type}
                        </CardDescription>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteDevice(device.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Status</span>
                      <Badge 
                        variant={device.status === 'active' ? 'default' : 'secondary'}
                        className={device.status === 'active' ? 'bg-green-600' : 'bg-gray-600'}
                      >
                        {device.status === 'active' ? (
                          <CheckCircle className="w-3 h-3 mr-1" />
                        ) : (
                          <XCircle className="w-3 h-3 mr-1" />
                        )}
                        {device.status}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Added</span>
                      <span className="text-white">
                        {new Date(device.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {device.last_active && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Last Active</span>
                        <span className="text-white">
                          {new Date(device.last_active).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default DeviceManagement;

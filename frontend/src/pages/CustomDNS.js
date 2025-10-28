import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Globe, Plus, Trash2, Shield, CheckCircle, Server, 
  Loader, AlertCircle
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
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CustomDNS = ({ user }) => {
  const [publicDNS, setPublicDNS] = useState([]);
  const [customDNS, setCustomDNS] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [adding, setAdding] = useState(false);
  const [newDNS, setNewDNS] = useState({
    name: '',
    primary_dns: '',
    secondary_dns: ''
  });

  useEffect(() => {
    fetchDNSData();
  }, []);

  const fetchDNSData = async () => {
    try {
      const [publicRes, customRes] = await Promise.all([
        axios.get(`${API}/dns/public`),
        axios.get(`${API}/dns/user/${user.id}`)
      ]);
      setPublicDNS(publicRes.data.servers || []);
      setCustomDNS(customRes.data.dns_configs || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch DNS data:', error);
      toast.error('Failed to load DNS settings');
      setLoading(false);
    }
  };

  const validateIP = (ip) => {
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(ip)) return false;
    const parts = ip.split('.');
    return parts.every(part => parseInt(part) >= 0 && parseInt(part) <= 255);
  };

  const handleAddCustomDNS = async () => {
    // Validation
    if (!newDNS.name.trim()) {
      toast.error('Please enter a DNS name');
      return;
    }
    if (!validateIP(newDNS.primary_dns)) {
      toast.error('Invalid primary DNS IP address');
      return;
    }
    if (newDNS.secondary_dns && !validateIP(newDNS.secondary_dns)) {
      toast.error('Invalid secondary DNS IP address');
      return;
    }

    setAdding(true);
    try {
      await axios.post(`${API}/dns/custom`, {
        user_id: user.id,
        name: newDNS.name,
        primary_dns: newDNS.primary_dns,
        secondary_dns: newDNS.secondary_dns || null
      });
      toast.success('Custom DNS added successfully');
      setNewDNS({ name: '', primary_dns: '', secondary_dns: '' });
      setOpenDialog(false);
      fetchDNSData();
    } catch (error) {
      console.error('Failed to add custom DNS:', error);
      toast.error(error.response?.data?.detail || 'Failed to add custom DNS');
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteCustomDNS = async (dnsId) => {
    try {
      await axios.delete(`${API}/dns/custom/${dnsId}`);
      toast.success('Custom DNS removed');
      fetchDNSData();
    } catch (error) {
      console.error('Failed to delete DNS:', error);
      toast.error('Failed to remove DNS');
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-green-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">DNS Management</h1>
          <p className="text-gray-400">Configure custom DNS servers for enhanced privacy</p>
        </div>

        {/* Info Alert */}
        <Alert className="mb-6 bg-blue-900/30 border-blue-500/50">
          <AlertCircle className="h-4 w-4 text-blue-400" />
          <AlertDescription className="text-gray-300">
            Custom DNS servers can enhance your privacy and bypass censorship. Use trusted DNS providers only.
          </AlertDescription>
        </Alert>

        {/* Public DNS Servers */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Globe className="w-5 h-5 text-green-400" />
              Public DNS Servers
            </CardTitle>
            <CardDescription className="text-gray-400">
              Popular and trusted DNS providers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {publicDNS.map((dns) => (
                <div key={dns.id} className="p-4 rounded-lg border border-gray-700 bg-gray-800/30">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-white font-semibold mb-1">{dns.name}</h3>
                      <p className="text-gray-400 text-sm">{dns.description}</p>
                    </div>
                    <Badge className="bg-green-600">{dns.provider}</Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <Server className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-400">Primary:</span>
                      <code className="text-white bg-gray-700 px-2 py-1 rounded">
                        {dns.primary_dns}
                      </code>
                    </div>
                    {dns.secondary_dns && (
                      <div className="flex items-center gap-2 text-sm">
                        <Server className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-400">Secondary:</span>
                        <code className="text-white bg-gray-700 px-2 py-1 rounded">
                          {dns.secondary_dns}
                        </code>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Custom DNS */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Custom DNS Servers
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Your personalized DNS configurations
                </CardDescription>
              </div>
              <Dialog open={openDialog} onOpenChange={setOpenDialog}>
                <DialogTrigger asChild>
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Custom DNS
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-gray-800 text-white border-gray-700">
                  <DialogHeader>
                    <DialogTitle>Add Custom DNS</DialogTitle>
                    <DialogDescription className="text-gray-400">
                      Configure your own DNS server
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div>
                      <Label htmlFor="dns-name">DNS Name</Label>
                      <Input
                        id="dns-name"
                        placeholder="My Custom DNS"
                        value={newDNS.name}
                        onChange={(e) => setNewDNS({...newDNS, name: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <div>
                      <Label htmlFor="primary-dns">Primary DNS Server *</Label>
                      <Input
                        id="primary-dns"
                        placeholder="1.1.1.1"
                        value={newDNS.primary_dns}
                        onChange={(e) => setNewDNS({...newDNS, primary_dns: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <div>
                      <Label htmlFor="secondary-dns">Secondary DNS Server (Optional)</Label>
                      <Input
                        id="secondary-dns"
                        placeholder="8.8.8.8"
                        value={newDNS.secondary_dns}
                        onChange={(e) => setNewDNS({...newDNS, secondary_dns: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <Button 
                      onClick={handleAddCustomDNS} 
                      disabled={adding}
                      className="w-full bg-blue-600 hover:bg-blue-700"
                    >
                      {adding ? (
                        <>
                          <Loader className="w-4 h-4 mr-2 animate-spin" />
                          Adding...
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4 mr-2" />
                          Add DNS
                        </>
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent>
            {customDNS.length === 0 ? (
              <div className="text-center py-12">
                <Globe className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-semibold text-white mb-2">No Custom DNS</h3>
                <p className="text-gray-400 mb-4">Add your first custom DNS server</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {customDNS.map((dns) => (
                  <div key={dns.id} className="p-4 rounded-lg border border-blue-500/30 bg-blue-900/20">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-green-400" />
                        <h3 className="text-white font-semibold">{dns.name}</h3>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteCustomDNS(dns.id)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <Server className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-400">Primary:</span>
                        <code className="text-white bg-gray-700 px-2 py-1 rounded">
                          {dns.primary_dns}
                        </code>
                      </div>
                      {dns.secondary_dns && (
                        <div className="flex items-center gap-2 text-sm">
                          <Server className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-400">Secondary:</span>
                          <code className="text-white bg-gray-700 px-2 py-1 rounded">
                            {dns.secondary_dns}
                          </code>
                        </div>
                      )}
                      <div className="text-xs text-gray-500 mt-2">
                        Added {new Date(dns.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CustomDNS;

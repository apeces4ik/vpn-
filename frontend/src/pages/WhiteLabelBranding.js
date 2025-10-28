import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Palette, Upload, Globe, Save, Loader, Check
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const WhiteLabelBranding = ({ user, organizationId }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [organization, setOrganization] = useState(null);
  const [branding, setBranding] = useState({
    logo_url: '',
    primary_color: '#3B82F6',
    secondary_color: '#8B5CF6',
    custom_domain: ''
  });

  useEffect(() => {
    if (organizationId) {
      fetchOrganization();
    } else {
      setLoading(false);
    }
  }, [organizationId]);

  const fetchOrganization = async () => {
    try {
      const response = await axios.get(`${API}/organizations/${organizationId}`);
      setOrganization(response.data);
      if (response.data.branding) {
        setBranding({
          logo_url: response.data.branding.logo_url || '',
          primary_color: response.data.branding.primary_color || '#3B82F6',
          secondary_color: response.data.branding.secondary_color || '#8B5CF6',
          custom_domain: response.data.branding.custom_domain || ''
        });
      }
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch organization:', error);
      toast.error('Failed to load branding settings');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/organizations/${organizationId}`, {
        branding: branding
      });
      toast.success('Branding settings saved successfully');
      fetchOrganization();
    } catch (error) {
      console.error('Failed to save branding:', error);
      toast.error(error.response?.data?.detail || 'Failed to save branding');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!organizationId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
        <div className="max-w-4xl mx-auto">
          <Alert className="bg-yellow-900/30 border-yellow-500/50">
            <AlertDescription className="text-gray-300">
              White-label branding is only available for corporate organizations.
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">White-Label Branding</h1>
          <p className="text-gray-400">Customize the look and feel for your organization</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Settings */}
          <div className="space-y-6">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Palette className="w-5 h-5 text-purple-400" />
                  Color Theme
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Choose your brand colors
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="primary-color" className="text-gray-300">Primary Color</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      id="primary-color"
                      type="color"
                      value={branding.primary_color}
                      onChange={(e) => setBranding({...branding, primary_color: e.target.value})}
                      className="w-20 h-10 p-1 bg-gray-700 border-gray-600"
                    />
                    <Input
                      value={branding.primary_color}
                      onChange={(e) => setBranding({...branding, primary_color: e.target.value})}
                      className="flex-1 bg-gray-700 border-gray-600 text-white"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="secondary-color" className="text-gray-300">Secondary Color</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      id="secondary-color"
                      type="color"
                      value={branding.secondary_color}
                      onChange={(e) => setBranding({...branding, secondary_color: e.target.value})}
                      className="w-20 h-10 p-1 bg-gray-700 border-gray-600"
                    />
                    <Input
                      value={branding.secondary_color}
                      onChange={(e) => setBranding({...branding, secondary_color: e.target.value})}
                      className="flex-1 bg-gray-700 border-gray-600 text-white"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Upload className="w-5 h-5 text-blue-400" />
                  Logo
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Upload your company logo
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="logo-url" className="text-gray-300">Logo URL</Label>
                  <Input
                    id="logo-url"
                    placeholder="https://yourcompany.com/logo.png"
                    value={branding.logo_url}
                    onChange={(e) => setBranding({...branding, logo_url: e.target.value})}
                    className="bg-gray-700 border-gray-600 text-white mt-1"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Globe className="w-5 h-5 text-green-400" />
                  Custom Domain
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Use your own domain
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="custom-domain" className="text-gray-300">Domain</Label>
                  <Input
                    id="custom-domain"
                    placeholder="vpn.yourcompany.com"
                    value={branding.custom_domain}
                    onChange={(e) => setBranding({...branding, custom_domain: e.target.value})}
                    className="bg-gray-700 border-gray-600 text-white mt-1"
                  />
                </div>
              </CardContent>
            </Card>

            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="w-full bg-purple-600 hover:bg-purple-700"
            >
              {saving ? (
                <>
                  <Loader className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Branding
                </>
              )}
            </Button>
          </div>

          {/* Preview */}
          <div>
            <Card className="bg-gray-800/50 border-gray-700 sticky top-6">
              <CardHeader>
                <CardTitle className="text-white">Preview</CardTitle>
                <CardDescription className="text-gray-400">
                  See how your branding looks
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div 
                  className="rounded-lg p-8 space-y-6"
                  style={{
                    background: `linear-gradient(135deg, ${branding.primary_color}20, ${branding.secondary_color}20)`
                  }}
                >
                  {/* Logo Preview */}
                  {branding.logo_url && (
                    <div className="flex justify-center">
                      <img 
                        src={branding.logo_url} 
                        alt="Logo" 
                        className="max-h-16"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                    </div>
                  )}

                  {/* Button Previews */}
                  <div className="space-y-3">
                    <button
                      className="w-full py-3 px-4 rounded-lg font-semibold text-white transition-all"
                      style={{ backgroundColor: branding.primary_color }}
                    >
                      Primary Button
                    </button>
                    <button
                      className="w-full py-3 px-4 rounded-lg font-semibold text-white transition-all"
                      style={{ backgroundColor: branding.secondary_color }}
                    >
                      Secondary Button
                    </button>
                  </div>

                  {/* Card Preview */}
                  <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 border border-white/20">
                    <div className="flex items-center gap-2 mb-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: branding.primary_color }}
                      />
                      <span className="text-white font-semibold">Preview Card</span>
                    </div>
                    <p className="text-gray-300 text-sm">
                      This is how your branded interface will look
                    </p>
                  </div>

                  {/* Domain Preview */}
                  {branding.custom_domain && (
                    <div className="text-center">
                      <div className="text-gray-400 text-sm mb-1">Your Domain</div>
                      <div className="text-white font-semibold">{branding.custom_domain}</div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WhiteLabelBranding;
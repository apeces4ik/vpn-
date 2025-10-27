import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Users,
  Shield,
  Activity,
  Database,
  AlertTriangle,
  CheckCircle,
  UserPlus,
  Settings,
  Key,
  Palette
} from 'lucide-react';
import './TeamDashboard.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001/api';

function TeamDashboard() {
  const [organizationId, setOrganizationId] = useState('');
  const [organization, setOrganization] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Organization creation
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgEmail, setNewOrgEmail] = useState('');
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState('');
  
  // Team member management
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('member');
  
  // White-label branding
  const [brandingLogoUrl, setBrandingLogoUrl] = useState('');
  const [brandingPrimaryColor, setBrandingPrimaryColor] = useState('#3B82F6');
  const [brandingSecondaryColor, setBrandingSecondaryColor] = useState('#10B981');

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      const response = await axios.get(`${API_URL}/tariffs`);
      setPlans(response.data);
      if (response.data.length > 0) {
        setSelectedPlan(response.data[1].id); // Default to Pro plan
      }
    } catch (err) {
      console.error('Error loading plans:', err);
    }
  };

  const createOrganization = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_URL}/organizations`, null, {
        params: {
          name: newOrgName,
          owner_email: newOrgEmail,
          plan_id: selectedPlan,
          max_team_members: 10
        }
      });
      
      setOrganizationId(response.data.organization_id);
      setNewOrgName('');
      setNewOrgEmail('');
      await loadDashboard(response.data.organization_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create organization');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboard = async (orgId = organizationId) => {
    if (!orgId) return;
    
    setLoading(true);
    setError('');
    try {
      // Load organization details
      const orgResponse = await axios.get(`${API_URL}/organizations/${orgId}`);
      setOrganization(orgResponse.data);
      
      // Load dashboard data
      const dashResponse = await axios.get(`${API_URL}/organizations/${orgId}/dashboard`);
      setDashboard(dashResponse.data);
      
      // Load team members
      const membersResponse = await axios.get(`${API_URL}/organizations/${orgId}/members`);
      setTeamMembers(membersResponse.data.members);
      
      // Load security events
      const eventsResponse = await axios.get(`${API_URL}/organizations/${orgId}/security/events?limit=20`);
      setSecurityEvents(eventsResponse.data.events);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const addTeamMember = async () => {
    if (!newMemberEmail) return;
    
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_URL}/organizations/${organizationId}/members`, null, {
        params: {
          email: newMemberEmail,
          role: newMemberRole
        }
      });
      
      setNewMemberEmail('');
      setNewMemberRole('member');
      await loadDashboard();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add team member');
    } finally {
      setLoading(false);
    }
  };

  const updateMemberRole = async (memberId, newRole) => {
    setLoading(true);
    setError('');
    try {
      await axios.put(`${API_URL}/organizations/${organizationId}/members/${memberId}`, null, {
        params: { role: newRole }
      });
      await loadDashboard();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update member role');
    } finally {
      setLoading(false);
    }
  };

  const removeMember = async (memberId) => {
    if (!window.confirm('Are you sure you want to remove this team member?')) return;
    
    setLoading(true);
    setError('');
    try {
      await axios.delete(`${API_URL}/organizations/${organizationId}/members/${memberId}`);
      await loadDashboard();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove team member');
    } finally {
      setLoading(false);
    }
  };

  const updateBranding = async () => {
    setLoading(true);
    setError('');
    try {
      await axios.put(`${API_URL}/organizations/${organizationId}`, null, {
        params: {
          branding: JSON.stringify({
            logo_url: brandingLogoUrl,
            primary_color: brandingPrimaryColor,
            secondary_color: brandingSecondaryColor
          })
        }
      });
      await loadDashboard();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update branding');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (severity) => {
    const colors = {
      info: 'bg-blue-500',
      warning: 'bg-yellow-500',
      critical: 'bg-red-500'
    };
    return <Badge className={colors[severity] || 'bg-gray-500'}>{severity}</Badge>;
  };

  const getRoleBadge = (role) => {
    const colors = {
      owner: 'bg-purple-500',
      admin: 'bg-blue-500',
      manager: 'bg-green-500',
      member: 'bg-gray-500'
    };
    return <Badge className={colors[role] || 'bg-gray-500'}>{role}</Badge>;
  };

  if (!organizationId) {
    return (
      <div className="team-dashboard-container">
        <div className="team-dashboard-header">
          <h1 className="text-4xl font-bold mb-4">Corporate Team Dashboard</h1>
          <p className="text-gray-400 mb-8">
            Manage your organization, team members, and monitor security
          </p>
        </div>

        <Card className="max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle>Create Organization</CardTitle>
            <CardDescription>
              Set up your corporate account to manage your team
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-4">
              <div>
                <Label htmlFor="orgName">Organization Name</Label>
                <Input
                  id="orgName"
                  placeholder="Enter organization name"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                />
              </div>
              
              <div>
                <Label htmlFor="ownerEmail">Owner Email</Label>
                <Input
                  id="ownerEmail"
                  type="email"
                  placeholder="owner@company.com"
                  value={newOrgEmail}
                  onChange={(e) => setNewOrgEmail(e.target.value)}
                />
              </div>
              
              <div>
                <Label htmlFor="plan">Plan</Label>
                <select
                  id="plan"
                  className="w-full p-2 border rounded-md bg-gray-800 text-white"
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value)}
                >
                  {plans.map(plan => (
                    <option key={plan.id} value={plan.id}>
                      {plan.name} - ${plan.price_monthly}/mo (Corporate)
                    </option>
                  ))}
                </select>
              </div>
              
              <Button
                onClick={createOrganization}
                disabled={loading || !newOrgName || !newOrgEmail}
                className="w-full"
              >
                {loading ? 'Creating...' : 'Create Organization'}
              </Button>
              
              <div className="mt-4 pt-4 border-t border-gray-700">
                <Label htmlFor="existingOrgId">Or Load Existing Organization</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    id="existingOrgId"
                    placeholder="Enter Organization ID"
                    onChange={(e) => setOrganizationId(e.target.value)}
                  />
                  <Button onClick={() => loadDashboard()}>Load</Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="team-dashboard-container">
      <div className="team-dashboard-header">
        <div>
          <h1 className="text-4xl font-bold mb-2">{organization?.name || 'Team Dashboard'}</h1>
          <p className="text-gray-400">Organization ID: {organizationId}</p>
        </div>
        <Button variant="outline" onClick={() => setOrganizationId('')}>
          Switch Organization
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Stats Overview */}
      <div className="stats-grid">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Members</CardTitle>
            <Users className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.stats?.active_members || 0} / {dashboard?.stats?.max_members || 0}
            </div>
            <p className="text-xs text-gray-400 mt-1">Team members</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Connections</CardTitle>
            <Activity className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.stats?.active_connections || 0}
            </div>
            <p className="text-xs text-gray-400 mt-1">VPN connections</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Data Usage</CardTitle>
            <Database className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.stats?.total_data_used_gb || 0} GB
            </div>
            <p className="text-xs text-gray-400 mt-1">Total data transferred</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Security Status</CardTitle>
            <Shield className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {dashboard?.security?.critical_events_7d === 0 ? (
                <CheckCircle className="inline-block" />
              ) : (
                <AlertTriangle className="inline-block text-red-500" />
              )}
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {dashboard?.security?.critical_events_7d || 0} critical alerts
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different sections */}
      <Tabs defaultValue="members" className="mt-8">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="members">
            <Users className="mr-2 h-4 w-4" />
            Team Members
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="mr-2 h-4 w-4" />
            Security Events
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Team Members Tab */}
        <TabsContent value="members">
          <Card>
            <CardHeader>
              <CardTitle>Team Members</CardTitle>
              <CardDescription>
                Manage your organization's team members and roles
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Add Member Form */}
              <div className="flex gap-2 mb-6 p-4 bg-gray-800 rounded-lg">
                <Input
                  placeholder="Email address"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  className="flex-1"
                />
                <select
                  className="p-2 border rounded-md bg-gray-700 text-white"
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value)}
                >
                  <option value="member">Member</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
                <Button onClick={addTeamMember} disabled={loading}>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Add Member
                </Button>
              </div>

              {/* Members List */}
              <div className="space-y-4">
                {teamMembers.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 bg-gray-800 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{member.email}</p>
                        {getRoleBadge(member.role)}
                      </div>
                      <p className="text-sm text-gray-400 mt-1">
                        Joined: {new Date(member.joined_at).toLocaleDateString()}
                      </p>
                    </div>
                    
                    {member.role !== 'owner' && (
                      <div className="flex gap-2">
                        <select
                          className="p-2 border rounded-md bg-gray-700 text-white text-sm"
                          value={member.role}
                          onChange={(e) => updateMemberRole(member.id, e.target.value)}
                          disabled={loading}
                        >
                          <option value="member">Member</option>
                          <option value="manager">Manager</option>
                          <option value="admin">Admin</option>
                        </select>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => removeMember(member.id)}
                          disabled={loading}
                        >
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Events Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security Events</CardTitle>
              <CardDescription>
                Monitor security events and activities in your organization
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {securityEvents.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">No security events yet</p>
                ) : (
                  securityEvents.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-4 p-4 bg-gray-800 rounded-lg"
                    >
                      <div className="flex-shrink-0 mt-1">
                        {event.severity === 'critical' ? (
                          <AlertTriangle className="h-5 w-5 text-red-500" />
                        ) : event.severity === 'warning' ? (
                          <AlertTriangle className="h-5 w-5 text-yellow-500" />
                        ) : (
                          <CheckCircle className="h-5 w-5 text-blue-500" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium">{event.event_type}</p>
                          {getSeverityBadge(event.severity)}
                        </div>
                        <p className="text-sm text-gray-300">{event.description}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(event.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <div className="space-y-6">
            {/* White-label Branding */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  <CardTitle>White-label Branding</CardTitle>
                </div>
                <CardDescription>
                  Customize your organization's branding
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="logoUrl">Logo URL</Label>
                    <Input
                      id="logoUrl"
                      placeholder="https://example.com/logo.png"
                      value={brandingLogoUrl}
                      onChange={(e) => setBrandingLogoUrl(e.target.value)}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="primaryColor">Primary Color</Label>
                      <div className="flex gap-2">
                        <Input
                          id="primaryColor"
                          type="color"
                          value={brandingPrimaryColor}
                          onChange={(e) => setBrandingPrimaryColor(e.target.value)}
                          className="w-20"
                        />
                        <Input
                          value={brandingPrimaryColor}
                          onChange={(e) => setBrandingPrimaryColor(e.target.value)}
                          placeholder="#3B82F6"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <Label htmlFor="secondaryColor">Secondary Color</Label>
                      <div className="flex gap-2">
                        <Input
                          id="secondaryColor"
                          type="color"
                          value={brandingSecondaryColor}
                          onChange={(e) => setBrandingSecondaryColor(e.target.value)}
                          className="w-20"
                        />
                        <Input
                          value={brandingSecondaryColor}
                          onChange={(e) => setBrandingSecondaryColor(e.target.value)}
                          placeholder="#10B981"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <Button onClick={updateBranding} disabled={loading}>
                    Update Branding
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Organization Info */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  <CardTitle>Organization Information</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Organization ID:</span>
                    <span className="font-mono">{organizationId}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Owner Email:</span>
                    <span>{organization?.owner_email}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Plan Expires:</span>
                    <span>
                      {organization?.plan_expires_at
                        ? new Date(organization.plan_expires_at).toLocaleDateString()
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Max Team Members:</span>
                    <span>{organization?.max_team_members || 10}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default TeamDashboard;

import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Key, Code, Users, CreditCard } from 'lucide-react';
import './PartnerAPI.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001/api';

function PartnerAPI() {
  const [partnerName, setPartnerName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Test API
  const [testEmail, setTestEmail] = useState('');
  const [testPlanId, setTestPlanId] = useState('');
  const [testUserId, setTestUserId] = useState('');

  const createAPIKey = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await axios.post(`${API_URL}/partner/api-keys`, null, {
        params: {
          partner_name: partnerName,
          allowed_operations: JSON.stringify(['create_user', 'manage_subscription']),
          rate_limit: 1000
        }
      });
      
      setApiKey(response.data.api_key);
      setSecretKey(response.data.secret_key);
      setSuccess('API Key created successfully! Please save these credentials securely.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create API key');
    } finally {
      setLoading(false);
    }
  };

  const testCreateUser = async () => {
    if (!apiKey || !secretKey || !testEmail || !testPlanId) {
      setError('Please fill in all fields');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await axios.post(`${API_URL}/partner/users`, null, {
        params: {
          api_key: apiKey,
          secret_key: secretKey,
          email: testEmail,
          plan_id: testPlanId,
          plan_duration_days: 30
        }
      });
      
      setTestUserId(response.data.user_id);
      setSuccess(`User created successfully! User ID: ${response.data.user_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  const testUpdateSubscription = async () => {
    if (!apiKey || !secretKey || !testUserId) {
      setError('Please create a user first or enter User ID');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      await axios.put(`${API_URL}/partner/users/${testUserId}/subscription`, null, {
        params: {
          api_key: apiKey,
          secret_key: secretKey,
          extend_days: 30
        }
      });
      
      setSuccess('Subscription extended successfully by 30 days!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update subscription');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="partner-api-container">
      <div className="partner-api-header">
        <h1 className="text-4xl font-bold mb-4">Partner API</h1>
        <p className="text-gray-400 mb-8">
          Integrate AnonVPN into your platform with our Partner API
        </p>
      </div>

      <Tabs defaultValue="overview" className="partner-api-tabs">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">
            <Key className="mr-2 h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="setup">
            <Code className="mr-2 h-4 w-4" />
            Setup
          </TabsTrigger>
          <TabsTrigger value="test">
            <Users className="mr-2 h-4 w-4" />
            Test API
          </TabsTrigger>
          <TabsTrigger value="docs">
            <CreditCard className="mr-2 h-4 w-4" />
            Documentation
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Partner API Overview</CardTitle>
              <CardDescription>
                Build powerful integrations with AnonVPN's Partner API
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold mb-3">Features</h3>
                  <ul className="space-y-2 text-gray-300">
                    <li>✅ Create users programmatically</li>
                    <li>✅ Manage user subscriptions</li>
                    <li>✅ Extend subscription durations</li>
                    <li>✅ Secure API key authentication</li>
                    <li>✅ Rate limiting (1000 requests/hour)</li>
                    <li>✅ Real-time user management</li>
                  </ul>
                </div>

                <div className="bg-gray-800 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold mb-3">Use Cases</h3>
                  <ul className="space-y-2 text-gray-300">
                    <li><strong>Reseller Programs:</strong> Create VPN accounts for your customers</li>
                    <li><strong>Enterprise Integrations:</strong> Automate user provisioning</li>
                    <li><strong>Affiliate Platforms:</strong> Reward users with VPN subscriptions</li>
                    <li><strong>Bundle Services:</strong> Include VPN in your product offerings</li>
                  </ul>
                </div>

                <div className="bg-blue-900/30 border border-blue-500/50 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold mb-3 text-blue-400">Getting Started</h3>
                  <p className="text-gray-300 mb-2">
                    1. Generate your API key in the "Setup" tab
                  </p>
                  <p className="text-gray-300 mb-2">
                    2. Test the API in the "Test API" tab
                  </p>
                  <p className="text-gray-300">
                    3. Refer to "Documentation" for integration examples
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Setup Tab */}
        <TabsContent value="setup">
          <Card>
            <CardHeader>
              <CardTitle>Generate API Keys</CardTitle>
              <CardDescription>
                Create your Partner API credentials
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              
              {success && (
                <Alert className="mb-4 bg-green-900/30 border-green-500/50">
                  <AlertDescription className="text-green-400">{success}</AlertDescription>
                </Alert>
              )}

              {!apiKey ? (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="partnerName">Partner Name</Label>
                    <Input
                      id="partnerName"
                      placeholder="Your Company Name"
                      value={partnerName}
                      onChange={(e) => setPartnerName(e.target.value)}
                    />
                  </div>

                  <Button
                    onClick={createAPIKey}
                    disabled={loading || !partnerName}
                    className="w-full"
                  >
                    {loading ? 'Creating...' : 'Generate API Keys'}
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <Label className="text-green-400">API Key</Label>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="flex-1 bg-gray-900 p-2 rounded text-sm break-all">
                        {apiKey}
                      </code>
                      <Button
                        size="sm"
                        onClick={() => navigator.clipboard.writeText(apiKey)}
                      >
                        Copy
                      </Button>
                    </div>
                  </div>

                  <div className="bg-gray-800 p-4 rounded-lg">
                    <Label className="text-green-400">Secret Key</Label>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="flex-1 bg-gray-900 p-2 rounded text-sm break-all">
                        {secretKey}
                      </code>
                      <Button
                        size="sm"
                        onClick={() => navigator.clipboard.writeText(secretKey)}
                      >
                        Copy
                      </Button>
                    </div>
                  </div>

                  <Alert className="bg-yellow-900/30 border-yellow-500/50">
                    <AlertDescription className="text-yellow-400">
                      ⚠️ Save these credentials securely. You won't be able to see them again!
                    </AlertDescription>
                  </Alert>

                  <Button
                    variant="outline"
                    onClick={() => {
                      setApiKey('');
                      setSecretKey('');
                      setPartnerName('');
                    }}
                    className="w-full"
                  >
                    Generate New Keys
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Test API Tab */}
        <TabsContent value="test">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Test API: Create User</CardTitle>
                <CardDescription>
                  Create a test user using your API credentials
                </CardDescription>
              </CardHeader>
              <CardContent>
                {error && (
                  <Alert variant="destructive" className="mb-4">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                {success && (
                  <Alert className="mb-4 bg-green-900/30 border-green-500/50">
                    <AlertDescription className="text-green-400">{success}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-4">
                  <div>
                    <Label>API Key</Label>
                    <Input
                      placeholder="Enter your API key"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                    />
                  </div>

                  <div>
                    <Label>Secret Key</Label>
                    <Input
                      placeholder="Enter your secret key"
                      value={secretKey}
                      onChange={(e) => setSecretKey(e.target.value)}
                    />
                  </div>

                  <div>
                    <Label>User Email</Label>
                    <Input
                      type="email"
                      placeholder="user@example.com"
                      value={testEmail}
                      onChange={(e) => setTestEmail(e.target.value)}
                    />
                  </div>

                  <div>
                    <Label>Plan ID</Label>
                    <Input
                      placeholder="Get from /api/tariffs endpoint"
                      value={testPlanId}
                      onChange={(e) => setTestPlanId(e.target.value)}
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Tip: Use GET /api/tariffs to get available plan IDs
                    </p>
                  </div>

                  <Button
                    onClick={testCreateUser}
                    disabled={loading}
                    className="w-full"
                  >
                    {loading ? 'Creating User...' : 'Create Test User'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Test API: Update Subscription</CardTitle>
                <CardDescription>
                  Extend subscription for a user
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label>User ID</Label>
                    <Input
                      placeholder="User ID from create user response"
                      value={testUserId}
                      onChange={(e) => setTestUserId(e.target.value)}
                    />
                  </div>

                  <Button
                    onClick={testUpdateSubscription}
                    disabled={loading || !testUserId}
                    className="w-full"
                  >
                    {loading ? 'Extending...' : 'Extend Subscription by 30 Days'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Documentation Tab */}
        <TabsContent value="docs">
          <Card>
            <CardHeader>
              <CardTitle>API Documentation</CardTitle>
              <CardDescription>
                Integration examples and API reference
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold mb-3">Authentication</h3>
                  <p className="text-gray-300 mb-2">
                    All Partner API endpoints require both <code>api_key</code> and <code>secret_key</code> parameters.
                  </p>
                  <div className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
                    <pre className="text-sm text-green-400">
{`// Example using cURL
curl -X POST "${API_URL}/partner/users" \\
  -d "api_key=YOUR_API_KEY" \\
  -d "secret_key=YOUR_SECRET_KEY" \\
  -d "email=user@example.com" \\
  -d "plan_id=PLAN_ID" \\
  -d "plan_duration_days=30"`}
                    </pre>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Create User</h3>
                  <p className="text-gray-300 mb-2">
                    <strong>POST</strong> <code>/api/partner/users</code>
                  </p>
                  <p className="text-gray-300 mb-2">Parameters:</p>
                  <ul className="text-gray-300 space-y-1 mb-4">
                    <li>• <code>api_key</code> (required): Your API key</li>
                    <li>• <code>secret_key</code> (required): Your secret key</li>
                    <li>• <code>email</code> (required): User email address</li>
                    <li>• <code>plan_id</code> (required): Subscription plan ID</li>
                    <li>• <code>plan_duration_days</code> (optional): Duration in days (default: 30)</li>
                  </ul>
                  <div className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
                    <pre className="text-sm text-green-400">
{`// JavaScript Example
const response = await fetch('${API_URL}/partner/users', {
  method: 'POST',
  body: new URLSearchParams({
    api_key: 'YOUR_API_KEY',
    secret_key: 'YOUR_SECRET_KEY',
    email: 'user@example.com',
    plan_id: 'PLAN_ID',
    plan_duration_days: 30
  })
});

const data = await response.json();
console.log('User ID:', data.user_id);`}
                    </pre>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Update Subscription</h3>
                  <p className="text-gray-300 mb-2">
                    <strong>PUT</strong> <code>/api/partner/users/{'{user_id}'}/subscription</code>
                  </p>
                  <p className="text-gray-300 mb-2">Parameters:</p>
                  <ul className="text-gray-300 space-y-1 mb-4">
                    <li>• <code>api_key</code> (required): Your API key</li>
                    <li>• <code>secret_key</code> (required): Your secret key</li>
                    <li>• <code>plan_id</code> (optional): New plan ID</li>
                    <li>• <code>extend_days</code> (optional): Extend subscription by days</li>
                  </ul>
                  <div className="bg-gray-900 p-4 rounded-lg overflow-x-auto">
                    <pre className="text-sm text-green-400">
{`// Python Example
import requests

response = requests.put(
    '${API_URL}/partner/users/USER_ID/subscription',
    params={
        'api_key': 'YOUR_API_KEY',
        'secret_key': 'YOUR_SECRET_KEY',
        'extend_days': 30
    }
)

print(response.json())`}
                    </pre>
                  </div>
                </div>

                <div className="bg-blue-900/30 border border-blue-500/50 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold mb-3 text-blue-400">Rate Limits</h3>
                  <p className="text-gray-300">
                    • 1000 requests per hour per API key<br/>
                    • Rate limit resets every hour<br/>
                    • HTTP 429 response if limit exceeded
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default PartnerAPI;

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  DollarSign, TrendingUp, Users, CreditCard, 
  Loader, Award, Calendar, CheckCircle
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AffiliateDashboard = ({ user }) => {
  const [affiliateData, setAffiliateData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [openRegister, setOpenRegister] = useState(false);
  const [formData, setFormData] = useState({
    company_name: '',
    website: '',
    tax_id: ''
  });

  useEffect(() => {
    fetchAffiliateData();
  }, []);

  const fetchAffiliateData = async () => {
    try {
      const response = await axios.get(`${API}/affiliate/dashboard/${user.id}`);
      setAffiliateData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch affiliate data:', error);
      if (error.response?.status === 404) {
        setLoading(false);
      }
    }
  };

  const handleRegister = async () => {
    if (!formData.company_name.trim()) {
      toast.error('Please enter company name');
      return;
    }

    setRegistering(true);
    try {
      await axios.post(`${API}/affiliate/register`, {
        user_id: user.id,
        company_name: formData.company_name,
        website: formData.website,
        tax_id: formData.tax_id
      });
      toast.success('Affiliate registration successful!');
      setOpenRegister(false);
      fetchAffiliateData();
    } catch (error) {
      console.error('Failed to register:', error);
      toast.error(error.response?.data?.detail || 'Failed to register as affiliate');
    } finally {
      setRegistering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!affiliateData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-green-900 to-gray-900 p-6">
        <div className="max-w-4xl mx-auto">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-12 text-center">
              <Award className="w-16 h-16 mx-auto mb-4 text-green-400" />
              <h2 className="text-2xl font-bold text-white mb-2">Become an Affiliate Partner</h2>
              <p className="text-gray-400 mb-6">
                Earn 30% commission on all sales you generate. Join our affiliate program today!
              </p>
              <Dialog open={openRegister} onOpenChange={setOpenRegister}>
                <DialogTrigger asChild>
                  <Button className="bg-green-600 hover:bg-green-700">
                    <Users className="w-4 h-4 mr-2" />
                    Register as Affiliate
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-gray-800 text-white border-gray-700">
                  <DialogHeader>
                    <DialogTitle>Affiliate Registration</DialogTitle>
                    <DialogDescription className="text-gray-400">
                      Fill in your details to become an affiliate partner
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div>
                      <Label htmlFor="company">Company Name *</Label>
                      <Input
                        id="company"
                        placeholder="Your Company"
                        value={formData.company_name}
                        onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <div>
                      <Label htmlFor="website">Website</Label>
                      <Input
                        id="website"
                        placeholder="https://yourwebsite.com"
                        value={formData.website}
                        onChange={(e) => setFormData({...formData, website: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <div>
                      <Label htmlFor="tax_id">Tax ID</Label>
                      <Input
                        id="tax_id"
                        placeholder="Tax identification number"
                        value={formData.tax_id}
                        onChange={(e) => setFormData({...formData, tax_id: e.target.value})}
                        className="bg-gray-700 border-gray-600 text-white"
                      />
                    </div>
                    <Button 
                      onClick={handleRegister} 
                      disabled={registering}
                      className="w-full bg-green-600 hover:bg-green-700"
                    >
                      {registering ? (
                        <>
                          <Loader className="w-4 h-4 mr-2 animate-spin" />
                          Registering...
                        </>
                      ) : (
                        'Register'
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-green-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">Affiliate Dashboard</h1>
              <p className="text-gray-400">Track your affiliate earnings and performance</p>
            </div>
            <Badge className="bg-green-600 text-lg px-4 py-2">
              <CheckCircle className="w-4 h-4 mr-2" />
              Active Partner
            </Badge>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <Card className="bg-gradient-to-br from-green-900/50 to-blue-900/50 border-green-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-300 text-sm mb-1">Total Earnings</p>
                  <p className="text-3xl font-bold text-white">
                    ${(affiliateData?.total_earnings || 0).toFixed(2)}
                  </p>
                </div>
                <DollarSign className="w-10 h-10 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Pending</p>
                  <p className="text-3xl font-bold text-yellow-400">
                    ${(affiliateData?.pending_earnings || 0).toFixed(2)}
                  </p>
                </div>
                <Calendar className="w-10 h-10 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Conversions</p>
                  <p className="text-3xl font-bold text-blue-400">
                    {affiliateData?.total_conversions || 0}
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Commission Rate</p>
                  <p className="text-3xl font-bold text-purple-400">
                    30%
                  </p>
                </div>
                <Award className="w-10 h-10 text-purple-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Company Info */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Partner Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-gray-400 text-sm mb-1">Company Name</div>
                <div className="text-white font-semibold">{affiliateData?.company_name}</div>
              </div>
              <div>
                <div className="text-gray-400 text-sm mb-1">Status</div>
                <Badge className="bg-green-600">{affiliateData?.status}</Badge>
              </div>
              <div>
                <div className="text-gray-400 text-sm mb-1">Joined</div>
                <div className="text-white">
                  {new Date(affiliateData?.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Earnings History */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Earnings History</CardTitle>
            <CardDescription className="text-gray-400">
              Recent affiliate earnings and payouts
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!affiliateData?.earnings || affiliateData.earnings.length === 0 ? (
              <div className="text-center py-12">
                <CreditCard className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-semibold text-white mb-2">No Earnings Yet</h3>
                <p className="text-gray-400">Start promoting to earn commissions</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700">
                    <TableHead className="text-gray-400">Date</TableHead>
                    <TableHead className="text-gray-400">Description</TableHead>
                    <TableHead className="text-gray-400">Status</TableHead>
                    <TableHead className="text-right text-gray-400">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {affiliateData.earnings.map((earning) => (
                    <TableRow key={earning.id} className="border-gray-700">
                      <TableCell className="text-gray-300">
                        {new Date(earning.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-gray-300">
                        {earning.description || 'Commission Earned'}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="default"
                          className={
                            earning.status === 'paid' ? 'bg-green-600' :
                            earning.status === 'approved' ? 'bg-blue-600' : 'bg-yellow-600'
                          }
                        >
                          {earning.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="text-green-400 font-bold">
                          ${(earning.amount || 0).toFixed(2)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AffiliateDashboard;
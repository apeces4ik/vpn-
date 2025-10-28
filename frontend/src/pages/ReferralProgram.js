import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Users, Copy, Check, DollarSign, TrendingUp, 
  Gift, Loader, Share2, UserPlus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ReferralProgram = ({ user }) => {
  const [referralData, setReferralData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchReferralData();
  }, []);

  const fetchReferralData = async () => {
    try {
      const response = await axios.get(`${API}/referrals/${user.id}/stats`);
      setReferralData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch referral data:', error);
      // If no referral code exists, try to create one
      if (error.response?.status === 404) {
        await createReferralCode();
      }
      setLoading(false);
    }
  };

  const createReferralCode = async () => {
    setCreating(true);
    try {
      await axios.post(`${API}/referrals/create`, {
        user_id: user.id
      });
      toast.success('Referral code created!');
      fetchReferralData();
    } catch (error) {
      console.error('Failed to create referral code:', error);
      toast.error('Failed to create referral code');
    } finally {
      setCreating(false);
    }
  };

  const copyReferralLink = () => {
    const referralLink = `${window.location.origin}?ref=${referralData.referral_code}`;
    navigator.clipboard.writeText(referralLink);
    setCopied(true);
    toast.success('Referral link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const copyReferralCode = () => {
    navigator.clipboard.writeText(referralData.referral_code);
    setCopied(true);
    toast.success('Referral code copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!referralData && !creating) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
        <div className="max-w-4xl mx-auto">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-12 text-center">
              <Gift className="w-16 h-16 mx-auto mb-4 text-purple-400" />
              <h2 className="text-2xl font-bold text-white mb-2">Create Your Referral Code</h2>
              <p className="text-gray-400 mb-6">
                Start earning rewards by inviting friends to AnonVPN
              </p>
              <Button 
                onClick={createReferralCode}
                className="bg-purple-600 hover:bg-purple-700"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Create Referral Code
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const referralLink = `${window.location.origin}?ref=${referralData?.referral_code}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Referral Program</h1>
          <p className="text-gray-400">Invite friends and earn 20% commission on their subscriptions</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <Card className="bg-gradient-to-br from-purple-900/50 to-blue-900/50 border-purple-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-300 text-sm mb-1">Total Referrals</p>
                  <p className="text-3xl font-bold text-white">
                    {referralData?.total_referrals || 0}
                  </p>
                </div>
                <Users className="w-10 h-10 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Successful</p>
                  <p className="text-3xl font-bold text-green-400">
                    {referralData?.successful_referrals || 0}
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-green-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Total Earnings</p>
                  <p className="text-3xl font-bold text-yellow-400">
                    ${(referralData?.total_commission || 0).toFixed(2)}
                  </p>
                </div>
                <DollarSign className="w-10 h-10 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Pending</p>
                  <p className="text-3xl font-bold text-blue-400">
                    ${(referralData?.pending_commission || 0).toFixed(2)}
                  </p>
                </div>
                <Gift className="w-10 h-10 text-blue-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Referral Code Card */}
        <Card className="mb-6 bg-gradient-to-r from-purple-900/50 to-pink-900/50 border-purple-500/30">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Share2 className="w-5 h-5" />
              Your Referral Code
            </CardTitle>
            <CardDescription className="text-gray-300">
              Share this code with friends to earn 20% commission
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-gray-300 text-sm mb-2 block">Referral Code</label>
              <div className="flex gap-2">
                <Input
                  value={referralData?.referral_code || ''}
                  readOnly
                  className="bg-gray-700 border-gray-600 text-white text-lg font-mono"
                />
                <Button 
                  onClick={copyReferralCode}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            <div>
              <label className="text-gray-300 text-sm mb-2 block">Referral Link</label>
              <div className="flex gap-2">
                <Input
                  value={referralLink}
                  readOnly
                  className="bg-gray-700 border-gray-600 text-white text-sm"
                />
                <Button 
                  onClick={copyReferralLink}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* How It Works */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">How It Works</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-white font-bold">1</span>
                </div>
                <h3 className="text-white font-semibold mb-2">Share Your Code</h3>
                <p className="text-gray-400 text-sm">
                  Send your referral link to friends and family
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-white font-bold">2</span>
                </div>
                <h3 className="text-white font-semibold mb-2">They Subscribe</h3>
                <p className="text-gray-400 text-sm">
                  Friends sign up using your referral code
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-white font-bold">3</span>
                </div>
                <h3 className="text-white font-semibold mb-2">Earn Rewards</h3>
                <p className="text-gray-400 text-sm">
                  Get 20% commission on all their payments
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Referral List */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Your Referrals</CardTitle>
            <CardDescription className="text-gray-400">
              People who signed up using your code
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!referralData?.referrals || referralData.referrals.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-semibold text-white mb-2">No Referrals Yet</h3>
                <p className="text-gray-400">Share your referral code to start earning</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700">
                    <TableHead className="text-gray-400">Date</TableHead>
                    <TableHead className="text-gray-400">Referral</TableHead>
                    <TableHead className="text-gray-400">Status</TableHead>
                    <TableHead className="text-right text-gray-400">Commission</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {referralData.referrals.map((referral) => (
                    <TableRow key={referral.id} className="border-gray-700">
                      <TableCell className="text-gray-300">
                        {new Date(referral.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-gray-300">
                        {referral.referred_email || 'User'}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant={referral.status === 'active' ? 'default' : 'secondary'}
                          className={referral.status === 'active' ? 'bg-green-600' : 'bg-gray-600'}
                        >
                          {referral.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="text-green-400 font-bold">
                          ${(referral.commission_earned || 0).toFixed(2)}
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

export default ReferralProgram;

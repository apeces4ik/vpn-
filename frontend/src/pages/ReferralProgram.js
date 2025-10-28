import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Users, Copy, Check, DollarSign, TrendingUp, 
  Gift, Loader, Share2, UserPlus, ArrowLeft, Sparkles, Award
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
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
    toast.success('Referral link copied to clipboard!');
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
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
        <Loader className="w-12 h-12 animate-spin text-purple-400" />
      </div>
    );
  }

  if (!referralData && !creating) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-pink-900">
        <div className="border-b border-gray-700/50 bg-gray-900/50 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group">
              <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
              <span className="font-medium">Back to Dashboard</span>
            </button>
          </div>
        </div>
        <div className="max-w-4xl mx-auto px-6 py-16">
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
            <CardContent className="p-16 text-center">
              <div className="inline-flex p-6 bg-purple-500/20 rounded-full mb-6">
                <Gift className="w-16 h-16 text-purple-400" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-3">Create Your Referral Code</h2>
              <p className="text-gray-400 text-lg mb-8">Start earning 20% rewards by inviting friends to AnonVPN</p>
              <Button onClick={createReferralCode} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8 py-6 text-lg font-semibold">
                <UserPlus className="w-5 h-5 mr-2" />
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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-pink-900">
      <div className="border-b border-gray-700/50 bg-gray-900/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors group">
            <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
            <span className="font-medium">Back to Dashboard</span>
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-3 bg-pink-500/20 rounded-xl">
              <Users className="w-8 h-8 text-pink-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Referral Program</h1>
              <p className="text-gray-400 mt-1">Earn 20% commission on your friends' subscriptions</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-200 text-sm font-medium mb-1">Total Referrals</p>
                  <p className="text-4xl font-bold text-white">{referralData?.total_referrals || 0}</p>
                </div>
                <div className="p-4 bg-purple-500/30 rounded-2xl">
                  <Users className="w-8 h-8 text-purple-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-200 text-sm font-medium mb-1">Successful</p>
                  <p className="text-4xl font-bold text-white">{referralData?.successful_referrals || 0}</p>
                </div>
                <div className="p-4 bg-green-500/30 rounded-2xl">
                  <TrendingUp className="w-8 h-8 text-green-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-yellow-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-yellow-200 text-sm font-medium mb-1">Total Earned</p>
                  <p className="text-4xl font-bold text-white">${(referralData?.total_commission || 0).toFixed(2)}</p>
                </div>
                <div className="p-4 bg-yellow-500/30 rounded-2xl">
                  <DollarSign className="w-8 h-8 text-yellow-300" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border-blue-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-200 text-sm font-medium mb-1">Pending</p>
                  <p className="text-4xl font-bold text-white">${(referralData?.pending_commission || 0).toFixed(2)}</p>
                </div>
                <div className="p-4 bg-blue-500/30 rounded-2xl">
                  <Gift className="w-8 h-8 text-blue-300" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-8 bg-gradient-to-br from-purple-900/50 to-pink-900/50 border-purple-500/40 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white text-2xl flex items-center gap-2">
              <Share2 className="w-6 h-6" />
              Your Referral Code
            </CardTitle>
            <CardDescription className="text-gray-300 text-base">Share this code with friends to earn 20% commission forever</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <label className="text-white font-semibold mb-2 block">Referral Code</label>
              <div className="flex gap-3">
                <Input value={referralData?.referral_code || ''} readOnly className="bg-gray-800 border-gray-600 text-white text-2xl font-mono h-14 text-center" />
                <Button onClick={copyReferralCode} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8 font-semibold">
                  {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                </Button>
              </div>
            </div>
            <div>
              <label className="text-white font-semibold mb-2 block">Referral Link</label>
              <div className="flex gap-3">
                <Input value={referralLink} readOnly className="bg-gray-800 border-gray-600 text-white h-14" />
                <Button onClick={copyReferralLink} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8 font-semibold">
                  {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-8 bg-gray-800/50 border-gray-700 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white text-2xl flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-yellow-400" />
              How It Works
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="inline-flex w-16 h-16 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full items-center justify-center mx-auto mb-4">
                  <span className="text-white font-bold text-2xl">1</span>
                </div>
                <h3 className="text-white font-bold text-xl mb-2">Share Your Link</h3>
                <p className="text-gray-400">Send your unique referral link to friends, family, or your audience</p>
              </div>
              <div className="text-center">
                <div className="inline-flex w-16 h-16 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full items-center justify-center mx-auto mb-4">
                  <span className="text-white font-bold text-2xl">2</span>
                </div>
                <h3 className="text-white font-bold text-xl mb-2">They Subscribe</h3>
                <p className="text-gray-400">Your friends sign up and choose any subscription plan</p>
              </div>
              <div className="text-center">
                <div className="inline-flex w-16 h-16 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full items-center justify-center mx-auto mb-4">
                  <span className="text-white font-bold text-2xl">3</span>
                </div>
                <h3 className="text-white font-bold text-xl mb-2">Earn 20% Forever</h3>
                <p className="text-gray-400">Get 20% commission on all their payments, recurring monthly!</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-white text-2xl">Your Referrals</CardTitle>
            <CardDescription className="text-gray-400 text-base">People who signed up using your code</CardDescription>
          </CardHeader>
          <CardContent>
            {!referralData?.referrals || referralData.referrals.length === 0 ? (
              <div className="text-center py-16">
                <div className="inline-flex p-6 bg-gray-700/50 rounded-full mb-6">
                  <Users className="w-16 h-16 text-gray-500" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">No Referrals Yet</h3>
                <p className="text-gray-400 text-lg">Share your referral code to start earning commissions!</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700">
                    <TableHead className="text-gray-400 font-semibold">Date</TableHead>
                    <TableHead className="text-gray-400 font-semibold">Referral</TableHead>
                    <TableHead className="text-gray-400 font-semibold">Status</TableHead>
                    <TableHead className="text-right text-gray-400 font-semibold">Commission</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {referralData.referrals.map((referral) => (
                    <TableRow key={referral.id} className="border-gray-700/50 hover:bg-gray-700/30">
                      <TableCell className="text-gray-300">{new Date(referral.created_at).toLocaleDateString()}</TableCell>
                      <TableCell className="text-gray-300">{referral.referred_email || 'User'}</TableCell>
                      <TableCell>
                        <Badge className={referral.status === 'active' ? 'bg-green-500/20 text-green-300 border-green-500/50' : 'bg-gray-600/20 text-gray-300'}>
                          {referral.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right"><span className="text-green-400 font-bold text-lg">${(referral.commission_earned || 0).toFixed(2)}</span></TableCell>
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
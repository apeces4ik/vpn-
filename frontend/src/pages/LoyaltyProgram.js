import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Award, TrendingUp, Gift, Star, Crown, Zap, 
  ArrowUpRight, Coins, Loader, Trophy
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
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

const TIER_INFO = {
  bronze: { icon: Award, color: 'text-orange-600', bg: 'bg-orange-600/20', name: 'Bronze', min: 0 },
  silver: { icon: Star, color: 'text-gray-400', bg: 'bg-gray-400/20', name: 'Silver', min: 1000 },
  gold: { icon: Trophy, color: 'text-yellow-500', bg: 'bg-yellow-500/20', name: 'Gold', min: 5000 },
  platinum: { icon: Crown, color: 'text-purple-500', bg: 'bg-purple-500/20', name: 'Platinum', min: 10000 }
};

const LoyaltyProgram = ({ user }) => {
  const [loyaltyData, setLoyaltyData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLoyaltyData();
  }, []);

  const fetchLoyaltyData = async () => {
    try {
      const [loyaltyRes, transactionsRes] = await Promise.all([
        axios.get(`${API}/loyalty/${user.id}`),
        axios.get(`${API}/loyalty/${user.id}/transactions`)
      ]);
      setLoyaltyData(loyaltyRes.data);
      setTransactions(transactionsRes.data.transactions || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch loyalty data:', error);
      toast.error('Failed to load loyalty program data');
      setLoading(false);
    }
  };

  const getTierProgress = () => {
    if (!loyaltyData) return 0;
    const currentTier = TIER_INFO[loyaltyData.tier];
    const tierKeys = Object.keys(TIER_INFO);
    const currentIndex = tierKeys.indexOf(loyaltyData.tier);
    
    if (currentIndex === tierKeys.length - 1) return 100; // Max tier
    
    const nextTier = TIER_INFO[tierKeys[currentIndex + 1]];
    const progress = ((loyaltyData.total_points - currentTier.min) / (nextTier.min - currentTier.min)) * 100;
    return Math.min(progress, 100);
  };

  const getNextTierName = () => {
    if (!loyaltyData) return '';
    const tierKeys = Object.keys(TIER_INFO);
    const currentIndex = tierKeys.indexOf(loyaltyData.tier);
    if (currentIndex === tierKeys.length - 1) return 'Max Level';
    return TIER_INFO[tierKeys[currentIndex + 1]].name;
  };

  const getNextTierPoints = () => {
    if (!loyaltyData) return 0;
    const tierKeys = Object.keys(TIER_INFO);
    const currentIndex = tierKeys.indexOf(loyaltyData.tier);
    if (currentIndex === tierKeys.length - 1) return loyaltyData.total_points;
    return TIER_INFO[tierKeys[currentIndex + 1]].min;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const CurrentTierIcon = TIER_INFO[loyaltyData?.tier]?.icon || Award;
  const tierInfo = TIER_INFO[loyaltyData?.tier] || TIER_INFO.bronze;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Loyalty Program</h1>
          <p className="text-gray-400">Earn points and unlock exclusive rewards</p>
        </div>

        {/* Current Status Card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card className="lg:col-span-2 bg-gradient-to-br from-purple-900/50 to-blue-900/50 border-purple-500/30">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <CurrentTierIcon className={`w-6 h-6 ${tierInfo.color}`} />
                {tierInfo.name} Member
              </CardTitle>
              <CardDescription className="text-gray-300">
                Your current membership level
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">Total Points</span>
                    <span className="text-3xl font-bold text-white">
                      {loyaltyData?.total_points || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm text-gray-400">
                    <span>Progress to {getNextTierName()}</span>
                    <span>{getNextTierPoints() - (loyaltyData?.total_points || 0)} points needed</span>
                  </div>
                  <Progress value={getTierProgress()} className="h-2 mt-2" />
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
                  <div>
                    <div className="text-gray-400 text-xs mb-1">Available Points</div>
                    <div className="text-2xl font-bold text-green-400">
                      {loyaltyData?.available_points || 0}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs mb-1">Redeemed</div>
                    <div className="text-2xl font-bold text-blue-400">
                      {loyaltyData?.redeemed_points || 0}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-xs mb-1">Referrals</div>
                    <div className="text-2xl font-bold text-purple-400">
                      {loyaltyData?.referral_count || 0}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tier Benefits */}
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Tier Benefits</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(TIER_INFO).map(([key, info]) => {
                  const TierIcon = info.icon;
                  const isUnlocked = loyaltyData && TIER_INFO[loyaltyData.tier].min >= info.min;
                  return (
                    <div 
                      key={key}
                      className={`flex items-center justify-between p-3 rounded-lg ${
                        isUnlocked ? info.bg : 'bg-gray-700/30'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <TierIcon className={`w-4 h-4 ${isUnlocked ? info.color : 'text-gray-600'}`} />
                        <span className={isUnlocked ? 'text-white' : 'text-gray-600'}>
                          {info.name}
                        </span>
                      </div>
                      <Badge variant={isUnlocked ? 'default' : 'secondary'}>
                        {info.min} pts
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Rewards Marketplace */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Gift className="w-5 h-5 text-purple-400" />
              Available Rewards
            </CardTitle>
            <CardDescription className="text-gray-400">
              Redeem your points for exclusive rewards
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { name: '1 Month Free', points: 500, icon: Zap, color: 'text-blue-400' },
                { name: 'Premium Server Access', points: 1000, icon: TrendingUp, color: 'text-green-400' },
                { name: 'Dedicated IP', points: 2000, icon: Crown, color: 'text-purple-400' }
              ].map((reward, index) => {
                const RewardIcon = reward.icon;
                const canRedeem = (loyaltyData?.available_points || 0) >= reward.points;
                return (
                  <div 
                    key={index}
                    className={`p-4 rounded-lg border ${
                      canRedeem 
                        ? 'border-purple-500/50 bg-purple-900/20' 
                        : 'border-gray-700 bg-gray-800/30'
                    }`}
                  >
                    <RewardIcon className={`w-8 h-8 mb-3 ${reward.color}`} />
                    <h3 className="text-white font-semibold mb-1">{reward.name}</h3>
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Coins className="w-4 h-4" />
                        <span className="font-bold">{reward.points}</span>
                      </div>
                      <Button 
                        size="sm" 
                        disabled={!canRedeem}
                        className="bg-purple-600 hover:bg-purple-700"
                      >
                        Redeem
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Transaction History */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Points History</CardTitle>
            <CardDescription className="text-gray-400">
              Recent points transactions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {transactions.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No transactions yet
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700">
                    <TableHead className="text-gray-400">Date</TableHead>
                    <TableHead className="text-gray-400">Type</TableHead>
                    <TableHead className="text-gray-400">Description</TableHead>
                    <TableHead className="text-right text-gray-400">Points</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((transaction) => (
                    <TableRow key={transaction.id} className="border-gray-700">
                      <TableCell className="text-gray-300">
                        {new Date(transaction.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant={transaction.transaction_type === 'earned' ? 'default' : 'secondary'}
                          className={transaction.transaction_type === 'earned' ? 'bg-green-600' : 'bg-red-600'}
                        >
                          {transaction.transaction_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-gray-300">
                        {transaction.description}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`font-bold ${
                          transaction.transaction_type === 'earned' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {transaction.transaction_type === 'earned' ? '+' : '-'}
                          {transaction.points}
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

export default LoyaltyProgram;

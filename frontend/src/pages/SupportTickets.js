import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  MessageSquare, Plus, Clock, CheckCircle, AlertCircle,
  Loader, Send, ArrowLeft, MessageCircle
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SupportTickets = ({ user }) => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTicket, setNewTicket] = useState({
    telegram_username: ''
  });

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API}/support/tickets/${user.id}`);
      setTickets(response.data.tickets || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
      toast.error('Failed to load support tickets');
      setLoading(false);
    }
  };

  const handleCreateTicket = async () => {
    if (!newTicket.telegram_username.trim()) {
      toast.error('Please enter your Telegram username');
      return;
    }

    setCreating(true);
    try {
      await axios.post(`${API}/support/tickets`, {
        user_id: user.id,
        telegram_username: newTicket.telegram_username,
        subject: 'Support Request',
        description: `Support request from Telegram user: @${newTicket.telegram_username}`,
        priority: 'medium',
        category: 'general'
      });
      toast.success('Support ticket created successfully');
      setNewTicket({ telegram_username: '' });
      setOpenDialog(false);
      fetchTickets();
    } catch (error) {
      console.error('Failed to create ticket:', error);
      toast.error(error.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setCreating(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return 'bg-red-500/20 text-red-300 border-red-500/50';
      case 'high': return 'bg-orange-500/20 text-orange-300 border-orange-500/50';
      case 'medium': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50';
      case 'low': return 'bg-green-500/20 text-green-300 border-green-500/50';
      default: return 'bg-gray-600/20 text-gray-300';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'resolved': return <CheckCircle className="w-4 h-4" />;
      case 'in_progress': return <Clock className="w-4 h-4" />;
      case 'open': return <AlertCircle className="w-4 h-4" />;
      default: return <MessageSquare className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <Loader className="w-12 h-12 animate-spin text-blue-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-cyan-900">
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
            <div className="p-3 bg-blue-500/20 rounded-xl">
              <MessageCircle className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">Support Center</h1>
              <p className="text-gray-400 mt-1">Get help from our support team</p>
            </div>
          </div>
        </div>

        <Alert className="mb-8 bg-blue-900/30 border-blue-500/50 backdrop-blur-xl">
          <MessageCircle className="h-5 w-5 text-blue-400" />
          <AlertDescription className="text-gray-300 text-base ml-2">
            <strong className="text-white">Need immediate assistance?</strong> Contact us on Telegram: <a href="https://t.me/ivasoft" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 font-semibold underline">@ivasoft</a>
          </AlertDescription>
        </Alert>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border-blue-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <p className="text-blue-200 text-sm font-medium mb-1">Total Tickets</p>
              <p className="text-4xl font-bold text-white">{tickets.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border-yellow-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <p className="text-yellow-200 text-sm font-medium mb-1">Open</p>
              <p className="text-4xl font-bold text-white">{tickets.filter(t => t.status === 'open').length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border-indigo-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <p className="text-indigo-200 text-sm font-medium mb-1">In Progress</p>
              <p className="text-4xl font-bold text-white">{tickets.filter(t => t.status === 'in_progress').length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30 backdrop-blur-xl">
            <CardContent className="p-6">
              <p className="text-green-200 text-sm font-medium mb-1">Resolved</p>
              <p className="text-4xl font-bold text-white">{tickets.filter(t => t.status === 'resolved').length}</p>
            </CardContent>
          </Card>
        </div>

        <div className="mb-8">
          <Dialog open={openDialog} onOpenChange={setOpenDialog}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 px-8 py-6 text-base font-semibold shadow-lg shadow-blue-500/30">
                <Plus className="w-5 h-5 mr-2" />
                Create New Ticket
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-gray-900 border-gray-700 backdrop-blur-xl max-w-2xl">
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold text-white">Create Support Ticket</DialogTitle>
                <DialogDescription className="text-gray-400 text-base">Enter your Telegram username and we'll contact you</DialogDescription>
              </DialogHeader>
              <div className="space-y-5 mt-6">
                <div>
                  <Label htmlFor="telegram_username" className="text-white font-semibold">Telegram Username *</Label>
                  <div className="relative mt-2">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg font-semibold">@</span>
                    <Input 
                      id="telegram_username" 
                      placeholder="your_username" 
                      value={newTicket.telegram_username} 
                      onChange={(e) => setNewTicket({...newTicket, telegram_username: e.target.value.replace('@', '')})} 
                      className="bg-gray-800 border-gray-600 text-white h-14 pl-10 text-lg" 
                    />
                  </div>
                  <p className="text-gray-500 text-sm mt-2">We'll contact you via Telegram to help with your issue</p>
                </div>
                <Button onClick={handleCreateTicket} disabled={creating} className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 h-14 text-base font-semibold mt-6">
                  {creating ? (<><Loader className="w-5 h-5 mr-2 animate-spin" />Creating...</>) : (<><Send className="w-5 h-5 mr-2" />Submit Support Request</>)}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        <div className="space-y-6">
          {tickets.length === 0 ? (
            <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-xl">
              <CardContent className="p-16 text-center">
                <div className="inline-flex p-6 bg-blue-500/20 rounded-full mb-6">
                  <MessageSquare className="w-16 h-16 text-blue-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">No Support Tickets</h3>
                <p className="text-gray-400 text-lg">Create a ticket if you need help with anything</p>
              </CardContent>
            </Card>
          ) : (
            tickets.map((ticket) => (
              <Card key={ticket.id} className="bg-gray-800/50 border-gray-700 backdrop-blur-xl hover:border-blue-500/50 transition-all group">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <CardTitle className="text-white text-xl font-bold">{ticket.subject}</CardTitle>
                        <Badge className={getPriorityColor(ticket.priority)}>{ticket.priority}</Badge>
                        <Badge variant="outline" className="text-gray-300 border-gray-600">{ticket.category}</Badge>
                      </div>
                      {ticket.telegram_username && (
                        <div className="mb-2">
                          <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/50 px-3 py-1">
                            <MessageCircle className="w-4 h-4 mr-1" />
                            @{ticket.telegram_username}
                          </Badge>
                        </div>
                      )}
                      <CardDescription className="text-gray-400 text-base">{ticket.description}</CardDescription>
                    </div>
                    <Badge className={ticket.status === 'resolved' ? 'bg-green-500/20 text-green-300 border-green-500/50 px-4 py-2' : ticket.status === 'in_progress' ? 'bg-blue-500/20 text-blue-300 border-blue-500/50 px-4 py-2' : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50 px-4 py-2'}>
                      {getStatusIcon(ticket.status)}
                      <span className="ml-2 font-semibold">{ticket.status}</span>
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm border-t border-gray-700 pt-4">
                    <div className="flex items-center gap-6 text-gray-400">
                      <span><strong className="text-white">Created:</strong> {new Date(ticket.created_at).toLocaleString()}</span>
                      {ticket.updated_at && <span><strong className="text-white">Updated:</strong> {new Date(ticket.updated_at).toLocaleDateString()}</span>}
                    </div>
                    {ticket.assigned_to && <span className="text-gray-400"><strong className="text-white">Assigned to:</strong> {ticket.assigned_to}</span>}
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

export default SupportTickets;
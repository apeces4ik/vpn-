import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { 
  Shield, AlertTriangle, CheckCircle, XCircle, 
  Activity, Clock, Loader, FileText
} from 'lucide-react';
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SecurityDashboard = ({ user, organizationId }) => {
  const [incidents, setIncidents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [incidentsRes, alertsRes, auditsRes] = await Promise.all([
        axios.get(`${API}/security/incidents`),
        axios.get(`${API}/alerts/active`),
        axios.get(`${API}/security/audits`)
      ]);
      setIncidents(incidentsRes.data.incidents || []);
      setAlerts(alertsRes.data.alerts || []);
      setAudits(auditsRes.data.audits || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch security data:', error);
      toast.error('Failed to load security dashboard');
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-orange-600';
      case 'medium': return 'bg-yellow-600';
      case 'low': return 'bg-green-600';
      default: return 'bg-gray-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'resolved': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'investigating': return <Activity className="w-4 h-4 text-blue-400" />;
      case 'open': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      default: return <XCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const criticalIncidents = incidents.filter(i => i.severity === 'critical');
  const activeAlerts = alerts.filter(a => a.status === 'active');
  const recentAudits = audits.slice(0, 5);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-red-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Security Dashboard</h1>
          <p className="text-gray-400">Monitor security incidents, alerts, and audits</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <Card className="bg-gradient-to-br from-red-900/50 to-orange-900/50 border-red-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-300 text-sm mb-1">Critical Incidents</p>
                  <p className="text-3xl font-bold text-white">
                    {criticalIncidents.length}
                  </p>
                </div>
                <AlertTriangle className="w-10 h-10 text-red-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Active Alerts</p>
                  <p className="text-3xl font-bold text-yellow-400">
                    {activeAlerts.length}
                  </p>
                </div>
                <Activity className="w-10 h-10 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Total Incidents</p>
                  <p className="text-3xl font-bold text-blue-400">
                    {incidents.length}
                  </p>
                </div>
                <Shield className="w-10 h-10 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Security Audits</p>
                  <p className="text-3xl font-bold text-green-400">
                    {audits.length}
                  </p>
                </div>
                <FileText className="w-10 h-10 text-green-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="incidents" className="space-y-4">
          <TabsList className="bg-gray-800 border-gray-700">
            <TabsTrigger value="incidents" className="data-[state=active]:bg-red-600">
              <AlertTriangle className="w-4 h-4 mr-2" />
              Incidents
            </TabsTrigger>
            <TabsTrigger value="alerts" className="data-[state=active]:bg-red-600">
              <Activity className="w-4 h-4 mr-2" />
              Alerts
            </TabsTrigger>
            <TabsTrigger value="audits" className="data-[state=active]:bg-red-600">
              <FileText className="w-4 h-4 mr-2" />
              Audits
            </TabsTrigger>
          </TabsList>

          {/* Incidents Tab */}
          <TabsContent value="incidents">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Security Incidents</CardTitle>
                <CardDescription className="text-gray-400">
                  Active and resolved security incidents
                </CardDescription>
              </CardHeader>
              <CardContent>
                {incidents.length === 0 ? (
                  <div className="text-center py-12">
                    <Shield className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-xl font-semibold text-white mb-2">No Incidents</h3>
                    <p className="text-gray-400">No security incidents reported</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-700">
                        <TableHead className="text-gray-400">Date</TableHead>
                        <TableHead className="text-gray-400">Title</TableHead>
                        <TableHead className="text-gray-400">Severity</TableHead>
                        <TableHead className="text-gray-400">Status</TableHead>
                        <TableHead className="text-gray-400">Description</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {incidents.map((incident) => (
                        <TableRow key={incident.id} className="border-gray-700">
                          <TableCell className="text-gray-300">
                            {new Date(incident.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-white font-semibold">
                            {incident.title}
                          </TableCell>
                          <TableCell>
                            <Badge className={getSeverityColor(incident.severity)}>
                              {incident.severity}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {getStatusIcon(incident.status)}
                              <span className="text-gray-300">{incident.status}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-gray-400 text-sm">
                            {incident.description}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Alerts Tab */}
          <TabsContent value="alerts">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Security Alerts</CardTitle>
                <CardDescription className="text-gray-400">
                  System-generated security alerts
                </CardDescription>
              </CardHeader>
              <CardContent>
                {alerts.length === 0 ? (
                  <div className="text-center py-12">
                    <Activity className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-xl font-semibold text-white mb-2">No Active Alerts</h3>
                    <p className="text-gray-400">All systems operating normally</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {alerts.map((alert) => (
                      <div 
                        key={alert.id}
                        className="p-4 rounded-lg border border-yellow-500/30 bg-yellow-900/20"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Activity className="w-5 h-5 text-yellow-400" />
                            <h3 className="text-white font-semibold">{alert.title}</h3>
                          </div>
                          <Badge className={getSeverityColor(alert.severity)}>
                            {alert.severity}
                          </Badge>
                        </div>
                        <p className="text-gray-300 text-sm mb-2">{alert.message}</p>
                        <div className="text-gray-400 text-xs">
                          {new Date(alert.created_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audits Tab */}
          <TabsContent value="audits">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Security Audits</CardTitle>
                <CardDescription className="text-gray-400">
                  Scheduled and completed security audits
                </CardDescription>
              </CardHeader>
              <CardContent>
                {audits.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-xl font-semibold text-white mb-2">No Audits</h3>
                    <p className="text-gray-400">No security audits scheduled</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-700">
                        <TableHead className="text-gray-400">Date</TableHead>
                        <TableHead className="text-gray-400">Type</TableHead>
                        <TableHead className="text-gray-400">Status</TableHead>
                        <TableHead className="text-gray-400">Findings</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {audits.map((audit) => (
                        <TableRow key={audit.id} className="border-gray-700">
                          <TableCell className="text-gray-300">
                            {new Date(audit.scheduled_date).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-white">
                            {audit.audit_type}
                          </TableCell>
                          <TableCell>
                            <Badge 
                              className={
                                audit.status === 'completed' ? 'bg-green-600' :
                                audit.status === 'in_progress' ? 'bg-blue-600' : 'bg-gray-600'
                              }
                            >
                              {audit.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-gray-400">
                            {audit.findings || 'N/A'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default SecurityDashboard;
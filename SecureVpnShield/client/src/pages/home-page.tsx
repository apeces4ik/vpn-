import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Link } from "wouter";
import { Loader2, Clock, ArrowRight, Activity } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function HomePage() {
  const { user, logoutMutation } = useAuth();
  const { toast } = useToast();

  const { data: servers } = useQuery({
    queryKey: ["/api/servers"],
  });

  const { data: connectionStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["/api/connection/status"],
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const connectMutation = useMutation({
    mutationFn: async (serverId: string) => {
      await apiRequest("POST", "/api/connect", { serverId });
    },
    onSuccess: () => {
      refetchStatus();
      toast({
        title: "VPN Connected",
        description: "You are now connected to the VPN server",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Connection Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", "/api/disconnect");
    },
    onSuccess: () => {
      refetchStatus();
      toast({
        title: "VPN Disconnected",
        description: "You have been disconnected from the VPN server",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Disconnection Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  const now = new Date();
  const trialStartTime = user?.trialStartTime ? new Date(user.trialStartTime) : null;
  const minutesLeft = trialStartTime
    ? Math.max(0, 60 - Math.floor((now.getTime() - trialStartTime.getTime()) / 60000))
    : 0;
  const trialExpired = minutesLeft === 0;

  if (!servers) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-border" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">SecureVPN Dashboard</h1>
          <div className="flex gap-4">
            <Link href="/subscription">
              <Button variant="outline">Subscription</Button>
            </Link>
            <Button variant="outline" onClick={() => logoutMutation.mutate()}>
              Logout
            </Button>
          </div>
        </div>

        {!user?.subscriptionActive && (
          <Card className="bg-primary/5">
            <CardHeader>
              <CardTitle className="text-white">Trial Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-white" />
                {minutesLeft > 0 ? (
                  <span className="text-white">{minutesLeft} minutes remaining in trial</span>
                ) : (
                  <span className="text-red-400">Trial expired</span>
                )}
              </div>
              {trialExpired && (
                <div className="flex items-center gap-2">
                  <Link href="/subscription">
                    <Button>
                      Subscribe Now
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!connectionStatus?.connected && (
          <div className="grid gap-4 md:grid-cols-3">
            {servers.map((server) => (
              <Card key={server.id}>
                <CardHeader>
                  <CardTitle>{server.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p>{server.location}</p>
                  <Button
                    className="mt-4 w-full"
                    onClick={() => connectMutation.mutate(server.id)}
                    disabled={connectMutation.isPending}
                  >
                    Connect
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {connectionStatus?.connected && (
          <Card className="bg-green-50 dark:bg-green-900/10">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Activity className="h-5 w-5 text-green-600 animate-pulse" />
                <span className="font-medium text-green-600">
                  Connected to VPN
                </span>
                <Button
                  variant="outline"
                  onClick={() => disconnectMutation.mutate()}
                  disabled={disconnectMutation.isPending}
                  className="ml-auto"
                >
                  Disconnect
                </Button>
              </div>
            </CardContent>
          </Card>
        )}


        {connectionStatus?.connected && (
          <div className="text-center">
            <Link href="/status">
              <Button variant="link">View Connection Status</Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
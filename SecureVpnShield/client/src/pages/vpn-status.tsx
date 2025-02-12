import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowLeft } from "lucide-react";

export default function VPNStatus() {
  const { user } = useAuth();
  const { data: servers } = useQuery({
    queryKey: ["/api/servers"],
  });

  const currentServer = servers?.find(s => s.id === user?.currentServer);

  if (!currentServer) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-2xl mx-auto">
          <Link href="/">
            <Button variant="ghost" className="mb-8">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Button>
          </Link>
          <Card>
            <CardContent className="pt-6">
              <p className="text-center text-muted-foreground">No active VPN connection</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-2xl mx-auto">
        <Link href="/">
          <Button variant="ghost" className="mb-8">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>

        <Card>
          <CardHeader>
            <CardTitle>VPN Connection Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-center gap-4 p-4 bg-primary/5 rounded-lg">
              <Activity className="h-6 w-6 text-primary animate-pulse" />
              <span className="font-medium">Connected</span>
            </div>

            <div className="grid gap-4">
              <div className="grid grid-cols-2 gap-2">
                <span className="text-muted-foreground">Server</span>
                <span className="font-medium">{currentServer.name}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <span className="text-muted-foreground">Location</span>
                <span className="font-medium">
                  {currentServer.flag} {currentServer.location}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <span className="text-muted-foreground">Status</span>
                <span className="font-medium text-green-600">Active</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <span className="text-muted-foreground">Subscription</span>
                <span className="font-medium">
                  {user?.subscriptionActive ? "Premium" : "Trial"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

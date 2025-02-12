import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/hooks/use-auth";
import NotFound from "@/pages/not-found";
import AuthPage from "@/pages/auth-page";
import HomePage from "@/pages/home-page";
import VPNStatus from "@/pages/vpn-status";
import SubscriptionPage from "@/pages/subscription-page";
import { ProtectedRoute } from "./lib/protected-route";
import { Logo } from "./components/ui/logo";

function Router() {
  return (
    <Switch>
      <Route path="/auth" component={AuthPage} />
      <ProtectedRoute path="/" component={HomePage} />
      <ProtectedRoute path="/status" component={VPNStatus} />
      <ProtectedRoute path="/subscription" component={SubscriptionPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <div className="min-h-screen gradient-bg text-foreground">
      <header className="glass-panel px-6 py-4">
        <Logo />
      </header>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Router />
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </div>
  );
}

export default App;
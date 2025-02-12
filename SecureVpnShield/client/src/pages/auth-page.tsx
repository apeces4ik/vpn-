import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { insertUserSchema } from "@shared/schema";
import { Shield, Wallet } from "lucide-react";
import { Redirect, useLocation } from "wouter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { initWeb3 } from "@/lib/web3";

// Отдельная схема для логина
const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export default function AuthPage() {
  const { user, loginMutation, registerMutation } = useAuth();
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const loginForm = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" }
  });

  const registerForm = useForm({
    resolver: zodResolver(insertUserSchema),
    defaultValues: { 
      username: "", 
      password: "", 
      email: "" 
    }
  });

  const walletLoginMutation = useMutation({
    mutationFn: async () => {
      const { web3 } = await initWeb3();
      const accounts = await web3.eth.getAccounts();
      const address = accounts[0];

      const message = "Login to SecureVPN";
      const signature = await web3.eth.personal.sign(message, address, "");

      const res = await apiRequest("POST", "/api/auth/wallet", { 
        address, 
        signature, 
        message 
      });
      return await res.json();
    },
    onSuccess: () => {
      setLocation("/");
      toast({
        title: "Success",
        description: "Successfully logged in with wallet",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Wallet login failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleLogin = async (data: z.infer<typeof loginSchema>) => {
    loginMutation.mutate(data, {
      onSuccess: () => setLocation("/")
    });
  };

  const handleRegister = async (data: z.infer<typeof insertUserSchema>) => {
    registerMutation.mutate(data, {
      onSuccess: () => setLocation("/")
    });
  };

  if (user) {
    return <Redirect to="/" />;
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 items-center">
        <div className="space-y-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">SecureVPN</h1>
            <p className="text-muted-foreground">
              Your trusted VPN service with servers worldwide. Start with a free trial and experience secure browsing today.
            </p>
          </div>

          <div className="grid gap-4">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              <span>Military-grade encryption</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              <span>Global server network</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              <span>1-hour free trial</span>
            </div>
          </div>
        </div>

        <Card className="bg-black border-white/10">
          <CardHeader>
            <CardTitle className="text-white text-2xl animate-[slideIn_0.5s_ease-out]">Welcome to SecureVPN</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="container mx-auto px-4 py-16">
              <div className="glass-panel max-w-md mx-auto p-8 rounded-xl">
                {/* Logo component needs to be defined */}
                <div>Logo Placeholder</div> {/* Placeholder until Logo component is defined */}
                <Tabs defaultValue="login">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">Login</TabsTrigger>
                    <TabsTrigger value="register">Register</TabsTrigger>
                  </TabsList>

                  <TabsContent value="login">
                    <div className="space-y-4">
                      <Form {...loginForm}>
                        <form onSubmit={loginForm.handleSubmit(handleLogin)} className="space-y-4">
                          <FormField
                            control={loginForm.control}
                            name="username"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Username</FormLabel>
                                <FormControl>
                                  <Input {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={loginForm.control}
                            name="password"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Password</FormLabel>
                                <FormControl>
                                  <Input type="password" {...field} />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
                            {loginMutation.isPending ? "Logging in..." : "Login"}
                          </Button>
                        </form>
                      </Form>

                      <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                          <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => walletLoginMutation.mutate()}
                        disabled={walletLoginMutation.isPending}
                      >
                        <Wallet className="w-4 h-4 mr-2" />
                        {walletLoginMutation.isPending ? "Connecting..." : "Connect Wallet"}
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="register">
                    <Form {...registerForm}>
                      <form onSubmit={registerForm.handleSubmit(handleRegister)} className="space-y-4">
                        <FormField
                          control={registerForm.control}
                          name="username"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Username</FormLabel>
                              <FormControl>
                                <Input {...field} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={registerForm.control}
                          name="password"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Password</FormLabel>
                              <FormControl>
                                <Input type="password" {...field} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={registerForm.control}
                          name="email"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>Email (optional)</FormLabel>
                              <FormControl>
                                <Input type="email" {...field} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
                          {registerMutation.isPending ? "Creating account..." : "Create Account"}
                        </Button>
                      </form>
                    </Form>
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
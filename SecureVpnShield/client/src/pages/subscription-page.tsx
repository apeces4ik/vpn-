import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Link } from "wouter";
import { ArrowLeft, CreditCard, Bitcoin, Apple, Check, Wallet2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { subscriptionPlans } from "@shared/schema";
import { purchaseSubscription } from "@/lib/web3";
import { useIsMobile } from "@/hooks/use-mobile";

export default function SubscriptionPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isMobile = useIsMobile();

  const standardSubscriptionMutation = useMutation({
    mutationFn: async ({ planId, paymentMethod }: { planId: string; paymentMethod: string }) => {
      await apiRequest("POST", "/api/subscribe", { planId, paymentMethod });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/user"] });
      toast({
        title: "Success!",
        description: "Your subscription has been activated.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Payment failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const cryptoSubscriptionMutation = useMutation({
    mutationFn: async ({ planId, price }: { planId: string; price: number }) => {
      await purchaseSubscription(planId, price);
      await apiRequest("POST", "/api/subscribe", { planId, paymentMethod: 'crypto' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/user"] });
      toast({
        title: "Success!",
        description: "Your crypto payment was successful and subscription has been activated.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Crypto payment failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handlePayment = (planId: string, paymentMethod: string) => {
    standardSubscriptionMutation.mutate({ planId, paymentMethod });
  };

  const now = new Date();
  const trialStartTime = user?.trialStartTime ? new Date(user.trialStartTime) : null;
  const minutesLeft = trialStartTime
    ? Math.max(0, 60 - Math.floor((now.getTime() - trialStartTime.getTime()) / 60000))
    : 0;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <Link href="/">
          <Button variant="ghost" className="mb-8">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>

        <div className="space-y-6">
          <h1 className="text-3xl font-bold">Choose Your Plan</h1>

          {!user?.subscriptionActive && minutesLeft === 0 && (
            <Card className="bg-primary/5 mb-6">
              <CardContent className="pt-6">
                <p className="text-lg mb-2 text-destructive">
                  Trial Status: Expired
                </p>
                <p className="text-muted-foreground">
                  Your trial has expired. Please choose a subscription plan to continue using the service.
                </p>
              </CardContent>
            </Card>
          )}

          <div className="grid md:grid-cols-3 gap-6">
            {subscriptionPlans.map((plan) => (
              <Card key={plan.id} className={`bg-black ${plan.id === 'pro' ? 'border-primary' : 'border-white/20'}`}>
                <CardHeader>
                  <CardTitle className="text-white">{plan.name}</CardTitle>
                  <CardDescription className="text-white/70">
                    {plan.price === 0 ? 'Free' : `$${plan.price}/month`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-center gap-2 text-white">
                        <Check className="h-4 w-4 text-white" />
                        {feature}
                      </li>
                    ))}
                  </ul>

                  {(plan.id !== 'free' || !user?.subscriptionActive) && (
                    <div className="space-y-2 pt-4">
                      <Button
                        className="w-full justify-start text-white border-white/20 hover:bg-white/10"
                        variant="outline"
                        onClick={() => {
                          const stripeHandler = window.open(
                            `/api/payment/stripe?plan=${plan.id}&amount=${plan.price * 100}`,
                            'stripe',
                            'width=600,height=600'
                          );
                        }}
                        disabled={standardSubscriptionMutation.isPending || (plan.id === 'free' && minutesLeft === 0)}
                      >
                        <CreditCard className="mr-2 h-4 w-4" />
                        {plan.price === 0 ? 'Start Free Trial' : 'Pay with Card/PayPal'}
                      </Button>

                      <Button
                        className="w-full justify-start text-white border-white/20 hover:bg-white/10"
                        variant="outline"
                        onClick={() => {
                          const sbpHandler = window.open(
                            `/api/payment/sbp?plan=${plan.id}&amount=${plan.price * 100}`,
                            'sbp',
                            'width=600,height=600'
                          );
                        }}
                        disabled={standardSubscriptionMutation.isPending || (plan.id === 'free' && minutesLeft === 0)}
                      >
                        <Wallet2 className="mr-2 h-4 w-4" />
                        {plan.price === 0 ? 'Start Free Trial' : 'Pay with СБП'}
                      </Button>

                      {plan.id !== 'free' && (
                        <Button
                          className="w-full justify-start text-white border-white/20 hover:bg-white/10"
                          variant="outline"
                          onClick={() => cryptoSubscriptionMutation.mutate({ 
                            planId: plan.id, 
                            price: plan.price / 2000 // Примерная конвертация USD в ETH
                          })}
                          disabled={cryptoSubscriptionMutation.isPending}
                        >
                          <Bitcoin className="mr-2 h-4 w-4" />
                          Pay with Crypto (~{(plan.price / 2000).toFixed(4)} ETH)
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
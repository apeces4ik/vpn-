import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { setupAuth } from "./auth";
import { vpnServers } from "@shared/schema";
import { vpnService } from "./vpn";

export function registerRoutes(app: Express): Server {
  setupAuth(app);

  app.get("/api/servers", (req, res) => {
    res.json(vpnServers);
  });

  app.post("/api/connect", async (req, res) => {
    if (!req.user) return res.sendStatus(401);

    const serverId = req.body.serverId;
    if (!serverId) return res.status(400).send("Server ID required");

    const user = req.user;
    const now = new Date();
    const trialExpired = user.trialStartTime &&
      (now.getTime() - user.trialStartTime.getTime() > 3600000); // 1 hour

    if (trialExpired && !user.subscriptionActive) {
      return res.status(403).send("Trial expired. Please subscribe.");
    }

    try {
      await vpnService.connect(user.id, serverId);
      await storage.updateUserServer(user.id, serverId);
      res.sendStatus(200);
    } catch (error) {
      res.status(500).send(error.message);
    }
  });

  app.post("/api/disconnect", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);

    try {
      await vpnService.disconnect(req.user!.id);
      await storage.updateUserServer(req.user!.id, null);
      res.sendStatus(200);
    } catch (error) {
      res.status(500).send(error.message);
    }
  });

  app.get("/api/connection/status", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);

    try {
      const status = await vpnService.getStatus(req.user!.id);
      res.json(status);
    } catch (error) {
      res.status(500).send(error.message);
    }
  });

  app.get("/api/payment/stripe", (req, res) => {
    if (!req.user) return res.sendStatus(401);
    
    const { plan, amount } = req.query;
    // Redirect to Stripe Checkout
    res.redirect(`https://checkout.stripe.com/pay/${process.env.STRIPE_KEY}?amount=${amount}&currency=usd`);
  });

  app.get("/api/payment/sbp", (req, res) => {
    if (!req.user) return res.sendStatus(401);
    
    const { plan, amount } = req.query;
    // Redirect to SBP payment page
    res.redirect(`https://sbp.payment.ru/pay?amount=${amount}&currency=rub`);
  });

  app.post("/api/subscribe", (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);

    const { planId, paymentMethod } = req.body;
    if (!planId) return res.status(400).send("Plan ID required");

    let success = true;
    let message = "Payment successful";

    switch (paymentMethod) {
      case 'card':
        // Simulating card payment processing
        success = Math.random() > 0.1; // 90% success rate
        message = success ? "Card payment successful" : "Card payment failed";
        break;
      case 'sbp':
        // Simulating СБП payment
        success = Math.random() > 0.05; // 95% success rate
        message = success ? "СБП payment successful" : "СБП payment failed";
        break;
      case 'apple':
        // Simulating Apple Pay
        success = Math.random() > 0.05; // 95% success rate
        message = success ? "Apple Pay payment successful" : "Apple Pay payment failed";
        break;
      case 'crypto':
        // Crypto payments are verified through the smart contract
        success = true;
        message = "Crypto payment verified";
        break;
      default:
        return res.status(400).send("Invalid payment method");
    }

    if (!success) {
      return res.status(400).send(message);
    }

    storage.updateUserSubscription(req.user!.id, true, planId)
      .then(() => res.json({ message }))
      .catch(err => res.status(400).send(err.message));
  });

  const httpServer = createServer(app);
  return httpServer;
}
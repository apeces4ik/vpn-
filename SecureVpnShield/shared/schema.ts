import { pgTable, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  email: text("email"),
  authProvider: text("auth_provider"), // 'local' или 'wallet'
  walletAddress: text("wallet_address"),
  trialStartTime: timestamp("trial_start_time"),
  subscriptionActive: boolean("subscription_active").default(false),
  subscriptionPlan: text("subscription_plan").default('free'), // 'free', 'standard', 'pro'
  currentServer: text("current_server"),
  hoursUsed: integer("hours_used").default(0),
});

// Базовая схема для создания пользователя
export const insertUserSchema = createInsertSchema(users, {
  username: z.string().min(1, "Username is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  email: z.string().email("Invalid email").optional().nullable(),
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export const vpnServers = [
  { id: "us-east", name: "US East", location: "New York", flag: "🇺🇸", speed: "1 Gbps" },
  { id: "us-west", name: "US West", location: "Los Angeles", flag: "🇺🇸", speed: "1 Gbps" },
  { id: "eu-central", name: "EU Central", location: "Frankfurt", flag: "🇩🇪", speed: "1 Gbps" },
  { id: "eu-west", name: "EU West", location: "London", flag: "🇬🇧", speed: "1 Gbps" },
  { id: "asia-east", name: "Asia East", location: "Tokyo", flag: "🇯🇵", speed: "1 Gbps" },
  { id: "asia-south", name: "Asia South", location: "Singapore", flag: "🇸🇬", speed: "1 Gbps" },
  { id: "au-east", name: "Australia", location: "Sydney", flag: "🇦🇺", speed: "1 Gbps" },
  { id: "ca-central", name: "Canada", location: "Toronto", flag: "🇨🇦", speed: "1 Gbps" },
];

export const subscriptionPlans = [
  {
    id: 'free',
    name: 'Free Trial',
    price: 0,
    hoursPerMonth: 1,
    features: [
      'Basic VPN access',
      'Limited server selection',
      '1 hour per month',
      'Standard support'
    ]
  },
  {
    id: 'standard',
    name: 'Standard',
    price: 10,
    hoursPerMonth: 100,
    features: [
      'Full VPN access',
      'All server locations',
      '100 hours per month',
      'Priority support',
      'No ads'
    ]
  },
  {
    id: 'pro',
    name: 'Professional',
    price: 25,
    hoursPerMonth: -1, // unlimited
    features: [
      'Unlimited VPN access',
      'All server locations',
      'Unlimited hours',
      '24/7 premium support',
      'No ads',
      'Multiple devices'
    ]
  }
];
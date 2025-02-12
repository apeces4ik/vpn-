import { User, InsertUser, vpnServers } from "@shared/schema";
import session from "express-session";
import createMemoryStore from "memorystore";

const MemoryStore = createMemoryStore(session);

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  getUserByWalletAddress(address: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  updateUserServer(userId: number, serverId: string): Promise<void>;
  updateUserSubscription(userId: number, isActive: boolean, plan?: string): Promise<void>;
  sessionStore: session.Store;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  currentId: number;
  sessionStore: session.Store;

  constructor() {
    this.users = new Map();
    this.currentId = 1;
    this.sessionStore = new MemoryStore({
      checkPeriod: 86400000,
    });
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.email === email,
    );
  }

  async getUserByWalletAddress(address: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.walletAddress === address,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentId++;
    const user: User = {
      ...insertUser,
      id,
      trialStartTime: new Date(),
      subscriptionActive: false,
      currentServer: null,
      hoursUsed: 0,
      subscriptionPlan: 'free',
      authProvider: insertUser.authProvider || 'local',
      walletAddress: insertUser.walletAddress || null,
    };
    this.users.set(id, user);
    return user;
  }

  async updateUserServer(userId: number, serverId: string): Promise<void> {
    const user = await this.getUser(userId);
    if (!user) throw new Error("User not found");

    if (!vpnServers.find(s => s.id === serverId)) {
      throw new Error("Invalid server");
    }

    this.users.set(userId, {
      ...user,
      currentServer: serverId
    });
  }

  async updateUserSubscription(userId: number, isActive: boolean, plan = 'standard'): Promise<void> {
    const user = await this.getUser(userId);
    if (!user) throw new Error("User not found");

    this.users.set(userId, {
      ...user,
      subscriptionActive: isActive,
      subscriptionPlan: plan
    });
  }
}

export const storage = new MemStorage();
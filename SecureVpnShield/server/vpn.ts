
import { spawn, type ChildProcess } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { vpnServers } from "@shared/schema";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface VPNConnection {
  process: ChildProcess;
  serverId: string;
  userId: number;
  startTime: Date;
}

class VPNService {
  private connections: Map<number, VPNConnection>;
  private configPath: string;

  constructor() {
    this.connections = new Map();
    this.configPath = path.join(__dirname, "..", "vpn-configs");
  }

  async connect(userId: number, serverId: string): Promise<void> {
    const server = vpnServers.find(s => s.id === serverId);
    if (!server) {
      throw new Error("Invalid VPN server selected");
    }

    await this.disconnect(userId);

    const configFile = path.join(this.configPath, `${serverId}.ovpn`);
    
    // Create unique credentials for this user
    const authFile = path.join(this.configPath, `auth-${userId}.txt`);
    await fs.writeFile(authFile, `vpn-user-${userId}\nvpn-pass-${userId}`);

    try {
      // Check if config exists
      await fs.access(configFile);

      // Start OpenVPN process
      const process = spawn("openvpn", [
        "--config", configFile,
        "--auth-user-pass", authFile,
        "--daemon",
        "--management", "127.0.0.1", `${5555 + userId}`,
      ]);

      // Handle errors
      process.on("error", (err: Error) => {
        console.error(`OpenVPN error for user ${userId}:`, err);
        this.connections.delete(userId);
      });

      // Log output for debugging
      process.stdout.on("data", (data: Buffer) => {
        console.log(`OpenVPN output for user ${userId}:`, data.toString());

        // Check for successful connection
        if (data.toString().includes("Initialization Sequence Completed")) {
          console.log(`VPN connection established for user ${userId}`);
        }
      });

      process.stderr.on("data", (data: Buffer) => {
        console.error(`OpenVPN error for user ${userId}:`, data.toString());
      });

      // Handle process exit
      process.on("exit", (code: number) => {
        console.log(`OpenVPN process exited with code ${code} for user ${userId}`);
        this.connections.delete(userId);
      });

      // Save connection info
      this.connections.set(userId, {
        process,
        serverId,
        userId,
        startTime: new Date()
      });

      // Wait for initial connection setup
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error("VPN connection timeout"));
        }, 10000);

        process.stdout.on("data", (data: Buffer) => {
          if (data.toString().includes("Initialization Sequence Completed")) {
            clearTimeout(timeout);
            resolve(undefined);
          }
        });

        process.on("error", (err) => {
          clearTimeout(timeout);
          reject(err);
        });
      });

    } catch (err) {
      const error = err as Error;
      throw new Error(`Failed to start VPN connection: ${error.message}`);
    }
  }

  async disconnect(userId: number): Promise<void> {
    const connection = this.connections.get(userId);
    if (connection) {
      // Kill OpenVPN process
      connection.process.kill();
      this.connections.delete(userId);

      // Update usage statistics
      const duration = (new Date().getTime() - connection.startTime.getTime()) / 3600000; // hours
      await this.updateUsageStats(userId, duration);
    }
  }

  async getStatus(userId: number): Promise<{
    connected: boolean;
    serverId: string | null;
    duration: number | null;
  }> {
    const connection = this.connections.get(userId);
    if (!connection) {
      return { connected: false, serverId: null, duration: null };
    }

    const duration = (new Date().getTime() - connection.startTime.getTime()) / 3600000;
    return {
      connected: true,
      serverId: connection.serverId,
      duration
    };
  }

  private async updateUsageStats(userId: number, hours: number): Promise<void> {
    // TODO: Update user's hoursUsed in database
    console.log(`User ${userId} used ${hours} hours`);
  }
}

export const vpnService = new VPNService();

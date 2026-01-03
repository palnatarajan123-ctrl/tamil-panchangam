import { type User, type InsertUser, type BirthDetails, type BaseChart } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  createBaseChart(details: BirthDetails): Promise<BaseChart>;
  getBaseChart(id: string): Promise<BaseChart | undefined>;
  listBaseCharts(): Promise<BaseChart[]>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private baseCharts: Map<string, BaseChart>;

  constructor() {
    this.users = new Map();
    this.baseCharts = new Map();
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async createBaseChart(details: BirthDetails): Promise<BaseChart> {
    const id = randomUUID();
    const createdAt = new Date().toISOString();
    
    const chart: BaseChart = {
      id,
      name: details.name,
      date_of_birth: details.dateOfBirth,
      time_of_birth: details.timeOfBirth,
      place_of_birth: details.placeOfBirth,
      latitude: details.latitude,
      longitude: details.longitude,
      timezone: details.timezone,
      status: "stub",
      message: "Base chart created. Astrology calculations pending implementation.",
      created_at: createdAt
    };
    
    this.baseCharts.set(id, chart);
    return chart;
  }

  async getBaseChart(id: string): Promise<BaseChart | undefined> {
    return this.baseCharts.get(id);
  }

  async listBaseCharts(): Promise<BaseChart[]> {
    return Array.from(this.baseCharts.values());
  }
}

export const storage = new MemStorage();

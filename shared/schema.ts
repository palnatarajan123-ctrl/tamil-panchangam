import { sql } from "drizzle-orm";
import { pgTable, text, varchar, doublePrecision, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

// Birth Chart Input Schema
export const birthDetailsSchema = z.object({
  name: z.string().min(1, "Name is required"),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  timeOfBirth: z.string().min(1, "Time of birth is required"),
  placeOfBirth: z.string().min(1, "Place of birth is required"),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  timezone: z.string().min(1, "Timezone is required"),
});

export type BirthDetails = z.infer<typeof birthDetailsSchema>;

// API request schema (snake_case for API compatibility)
export const createChartRequestSchema = z.object({
  name: z.string().min(1, "Name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  time_of_birth: z.string().min(1, "Time of birth is required"),
  place_of_birth: z.string().min(1, "Place of birth is required"),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  timezone: z.string().min(1, "Timezone is required"),
});

export type CreateChartRequest = z.infer<typeof createChartRequestSchema>;

// Base Chart Response
export interface BaseChart {
  id: string;
  name: string;
  date_of_birth: string;
  time_of_birth: string;
  place_of_birth: string;
  latitude: number;
  longitude: number;
  timezone: string;
  status: string;
  message: string;
  created_at: string;
}

// Monthly Prediction Request Schema
export const monthlyPredictionRequestSchema = z.object({
  base_chart_id: z.string().min(1, "Chart ID is required"),
  year: z.number().min(1900).max(2100),
  months: z.array(z.number().min(1).max(12)).min(1, "Select at least one month"),
});

export type MonthlyPredictionRequest = z.infer<typeof monthlyPredictionRequestSchema>;

// Prediction Response
export interface MonthlyPrediction {
  base_chart_id: string;
  year: number;
  months: number[];
  status: string;
  message: string;
  generated_at: string;
}

// Health Check Response
export interface HealthStatus {
  status: string;
  service: string;
  ayanamsa: string;
  calculation_method: string;
}

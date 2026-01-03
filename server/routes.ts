import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { createChartRequestSchema, monthlyPredictionRequestSchema, type BirthDetails } from "@shared/schema";
import { fromZodError } from "zod-validation-error";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // Health check endpoint
  app.get("/api/health", (req, res) => {
    res.json({
      status: "ok",
      service: "Tamil Panchangam Engine",
      ayanamsa: "Lahiri",
      calculation_method: "Drik Ganita"
    });
  });

  // Base Chart Service
  app.post("/api/base-chart/create", async (req, res) => {
    const parseResult = createChartRequestSchema.safeParse(req.body);
    
    if (!parseResult.success) {
      const error = fromZodError(parseResult.error);
      res.status(400).json({ error: error.message });
      return;
    }

    const data = parseResult.data;
    const birthDetails: BirthDetails = {
      name: data.name,
      dateOfBirth: data.date_of_birth,
      timeOfBirth: data.time_of_birth,
      placeOfBirth: data.place_of_birth,
      latitude: data.latitude,
      longitude: data.longitude,
      timezone: data.timezone,
    };

    const chart = await storage.createBaseChart(birthDetails);
    res.json(chart);
  });

  app.get("/api/base-chart/list", async (req, res) => {
    const charts = await storage.listBaseCharts();
    res.json(charts);
  });

  app.get("/api/base-chart/:chartId", async (req, res) => {
    const { chartId } = req.params;
    const chart = await storage.getBaseChart(chartId);
    
    if (!chart) {
      res.status(404).json({ error: "Chart not found" });
      return;
    }
    
    res.json(chart);
  });

  // Prediction Service
  app.post("/api/prediction/monthly", async (req, res) => {
    const parseResult = monthlyPredictionRequestSchema.safeParse(req.body);
    
    if (!parseResult.success) {
      const error = fromZodError(parseResult.error);
      res.status(400).json({ error: error.message });
      return;
    }

    const request = parseResult.data;
    
    // Verify the base chart exists
    const chart = await storage.getBaseChart(request.base_chart_id);
    if (!chart) {
      res.status(404).json({ error: "Base chart not found" });
      return;
    }
    
    res.json({
      base_chart_id: request.base_chart_id,
      year: request.year,
      months: request.months,
      status: "stub",
      message: "Monthly prediction service initialized. Transit and prediction logic pending implementation.",
      generated_at: new Date().toISOString()
    });
  });

  app.get("/api/prediction/transits/:chartId", async (req, res) => {
    const { chartId } = req.params;
    
    const chart = await storage.getBaseChart(chartId);
    if (!chart) {
      res.status(404).json({ error: "Base chart not found" });
      return;
    }
    
    res.json({
      chart_id: chartId,
      status: "stub",
      message: "Transit calculation pending implementation",
      transits: []
    });
  });

  return httpServer;
}

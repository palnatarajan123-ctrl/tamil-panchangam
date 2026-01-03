import { useState } from "react";
import { HeroSection } from "@/components/hero-section";
import { ChartForm } from "@/components/chart-form";
import { ChartList } from "@/components/chart-list";
import { useLocation } from "wouter";

export default function Home() {
  const [, navigate] = useLocation();

  const handleChartCreated = (chartId: string) => {
    navigate(`/chart/${chartId}`);
  };

  const handleViewChart = (chartId: string) => {
    navigate(`/chart/${chartId}`);
  };

  return (
    <div className="min-h-screen">
      <HeroSection />
      
      <section className="py-12 bg-muted/30">
        <div className="container max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <ChartForm onSuccess={handleChartCreated} />
            </div>
            <div>
              <ChartList onViewChart={handleViewChart} />
            </div>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="container max-w-7xl mx-auto px-4">
          <div className="text-center space-y-4 mb-12">
            <h2 className="text-3xl font-serif font-bold">How It Works</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our engine uses precise astronomical calculations based on Swiss Ephemeris
              to generate accurate Vedic astrology charts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center space-y-4 p-6">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <span className="text-xl font-bold text-primary">1</span>
              </div>
              <h3 className="font-semibold text-lg">Enter Birth Details</h3>
              <p className="text-sm text-muted-foreground">
                Provide accurate date, time, and location of birth for precise calculations.
              </p>
            </div>

            <div className="text-center space-y-4 p-6">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <span className="text-xl font-bold text-primary">2</span>
              </div>
              <h3 className="font-semibold text-lg">Generate Chart</h3>
              <p className="text-sm text-muted-foreground">
                Our engine computes planetary positions using Drik Ganita with Lahiri Ayanamsa.
              </p>
            </div>

            <div className="text-center space-y-4 p-6">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <span className="text-xl font-bold text-primary">3</span>
              </div>
              <h3 className="font-semibold text-lg">Explore Predictions</h3>
              <p className="text-sm text-muted-foreground">
                View Panchangam, Dasha periods, and monthly predictions with detailed analysis.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t py-8 bg-muted/20">
        <div className="container max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              All systems operational
            </div>
            <div className="text-sm text-muted-foreground font-mono">
              Drik Ganita | Lahiri Ayanamsa | Swiss Ephemeris
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

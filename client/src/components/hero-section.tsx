import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Sparkles, Calendar } from "lucide-react";
import { SouthIndianChart } from "./south-indian-chart";

export function HeroSection() {
  const samplePlanets = {
    "Su": 0,
    "Mo": 3,
    "Ma": 6,
    "Me": 0,
    "Ju": 9,
    "Ve": 1,
    "Sa": 10,
    "Ra": 5,
    "Ke": 11,
  };

  return (
    <section className="relative overflow-hidden py-16 md:py-24">
      <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.02]">
        <svg className="w-full h-full" viewBox="0 0 800 800" fill="none">
          <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
            <rect width="80" height="80" fill="none" stroke="currentColor" strokeWidth="0.5" />
            <line x1="0" y1="0" x2="80" y2="80" stroke="currentColor" strokeWidth="0.3" />
            <line x1="80" y1="0" x2="0" y2="80" stroke="currentColor" strokeWidth="0.3" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="container max-w-7xl mx-auto px-4 relative">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-8 text-center lg:text-left">
            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif font-bold tracking-tight">
                Tamil Panchangam
                <span className="block text-primary">Astrology Engine</span>
              </h1>
              <p className="text-lg md:text-xl text-muted-foreground max-w-xl mx-auto lg:mx-0">
                Precise Vedic astrology calculations using <strong>Drik Ganita</strong> method 
                with <strong>Lahiri Ayanamsa</strong>. Traditional South Indian chart style 
                with modern accuracy.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link href="/">
                <Button size="lg" className="w-full sm:w-auto gap-2" data-testid="button-create-chart-hero">
                  <Sparkles className="h-5 w-5" />
                  Create Birth Chart
                </Button>
              </Link>
              <Link href="/predictions">
                <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2" data-testid="button-view-predictions-hero">
                  <Calendar className="h-5 w-5" />
                  View Sample Prediction
                </Button>
              </Link>
            </div>

            <div className="flex items-center justify-center lg:justify-start gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>Traditional Vedic calculations with astronomical precision</span>
            </div>
          </div>

          <div className="flex justify-center lg:justify-end">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-transparent rounded-lg blur-3xl" />
              <div className="relative bg-card rounded-lg p-6 border">
                <SouthIndianChart lagna={0} planets={samplePlanets} size={420} />
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground font-mono">Drik Ganita</span>
                    <span className="text-muted-foreground font-mono">Lahiri Ayanamsa</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

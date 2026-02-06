import { useState, useEffect } from "react";
import { SouthIndianChart } from "@/components/south-indian-chart";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ChartData {
  lagna: number;
  planets: Record<string, number>;
  dignity?: Record<string, "exalted" | "debilitated" | "neutral">;
}

interface DivisionalCharts {
  D1: ChartData;
  D2?: ChartData;
  D7?: ChartData;
  D9: ChartData;
  D10?: ChartData;
}

interface TabbedChartViewerProps {
  charts: DivisionalCharts;
  onTabChange?: (tab: string) => void;
}

const CHART_INFO: Record<string, { title: string; subtitle: string; purpose: string; description: string }> = {
  D1: {
    title: "Rasi Chart (D1)",
    subtitle: "Core Birth Chart",
    purpose: "Foundation of all predictions",
    description: "The primary birth chart showing planetary positions at the exact moment of birth. All other charts derive from this foundation."
  },
  D2: {
    title: "Hora Chart (D2)",
    subtitle: "Wealth & Sustenance",
    purpose: "Financial capacity and resources",
    description: "Divides each sign into 2 parts (Sun/Moon horas). Sun hora indicates self-earned wealth; Moon hora suggests inherited or accumulated wealth."
  },
  D7: {
    title: "Saptamsa (D7)",
    subtitle: "Creativity & Children",
    purpose: "Creative potential and progeny",
    description: "Divides each sign into 7 parts, revealing creative abilities and matters related to children and artistic pursuits."
  },
  D9: {
    title: "Navamsa (D9)",
    subtitle: "Dharma & Maturity",
    purpose: "Spiritual growth and marriage",
    description: "The most important divisional chart after D1. Shows spiritual evolution, marriage quality, and how planetary promises manifest in the second half of life."
  },
  D10: {
    title: "Dasamsa (D10)",
    subtitle: "Career & Authority",
    purpose: "Professional life and status",
    description: "Divides each sign into 10 parts, revealing career potential, professional achievements, and societal recognition."
  },
};

export function TabbedChartViewer({ charts, onTabChange }: TabbedChartViewerProps) {
  const availableCharts = Object.entries(charts).filter(
    ([_, data]) => data && Object.keys(data.planets || {}).length > 0
  );

  const chartOrder = ["D1", "D9", "D10", "D7", "D2"];
  const firstAvailable = chartOrder.find(key => 
    availableCharts.some(([k]) => k === key)
  ) || "D1";

  const [activeTab, setActiveTab] = useState(firstAvailable);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    onTabChange?.(tab);
  };

  useEffect(() => {
    const isCurrentAvailable = availableCharts.some(([k]) => k === activeTab);
    if (!isCurrentAvailable && firstAvailable !== activeTab) {
      setActiveTab(firstAvailable);
      onTabChange?.(firstAvailable);
    }
  }, [charts, activeTab, firstAvailable, availableCharts, onTabChange]);
  
  // Notify parent of initial tab
  useEffect(() => {
    onTabChange?.(firstAvailable);
  }, []);

  return (
    <Card className="border-muted" data-testid="card-tabbed-charts">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <div className="border-b px-4 pt-4">
          <TabsList className="grid w-full grid-cols-5 h-auto gap-1" data-testid="tabs-chart-selector">
            {["D1", "D9", "D10", "D7", "D2"].map((chartKey) => {
              const chartData = charts[chartKey as keyof DivisionalCharts];
              const hasData = chartData && Object.keys(chartData.planets || {}).length > 0;
              
              return (
                <TabsTrigger
                  key={chartKey}
                  value={chartKey}
                  disabled={!hasData}
                  className="text-xs sm:text-sm py-2"
                  data-testid={`tab-${chartKey.toLowerCase()}`}
                >
                  {chartKey}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </div>

        {availableCharts.map(([key, data]) => {
          const info = CHART_INFO[key];
          return (
            <TabsContent key={key} value={key} className="mt-0">
              <CardContent className="pt-6 pb-8 overflow-x-auto">
                <div className="flex flex-col items-center gap-4">
                  <div className="text-center mb-2">
                    <h3 className="text-lg font-semibold">{info.title}</h3>
                    <p className="text-sm text-muted-foreground">{info.purpose}</p>
                  </div>
                  <SouthIndianChart
                    lagna={data.lagna}
                    planets={data.planets}
                    dignity={data.dignity}
                    size={480}
                    title={info.title}
                    subtitle={info.subtitle}
                    className="max-w-full h-auto"
                  />
                  <p className="text-xs text-muted-foreground text-center max-w-md mt-2">
                    {info.description}
                  </p>
                </div>
              </CardContent>
            </TabsContent>
          );
        })}
      </Tabs>
    </Card>
  );
}

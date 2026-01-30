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
}

const CHART_INFO: Record<string, { title: string; subtitle: string; purpose: string }> = {
  D1: {
    title: "Rasi Chart (D1)",
    subtitle: "Core Birth Chart",
    purpose: "Foundation of all predictions"
  },
  D2: {
    title: "Hora Chart (D2)",
    subtitle: "Wealth & Sustenance",
    purpose: "Financial capacity and resources"
  },
  D7: {
    title: "Saptamsa (D7)",
    subtitle: "Creativity & Children",
    purpose: "Creative potential and progeny"
  },
  D9: {
    title: "Navamsa (D9)",
    subtitle: "Dharma & Maturity",
    purpose: "Spiritual growth and marriage"
  },
  D10: {
    title: "Dasamsa (D10)",
    subtitle: "Career & Authority",
    purpose: "Professional life and status"
  },
};

export function TabbedChartViewer({ charts }: TabbedChartViewerProps) {
  const availableCharts = Object.entries(charts).filter(
    ([_, data]) => data && Object.keys(data.planets || {}).length > 0
  );

  const chartOrder = ["D1", "D9", "D10", "D7", "D2"];
  const firstAvailable = chartOrder.find(key => 
    availableCharts.some(([k]) => k === key)
  ) || "D1";

  const [activeTab, setActiveTab] = useState(firstAvailable);

  useEffect(() => {
    const isCurrentAvailable = availableCharts.some(([k]) => k === activeTab);
    if (!isCurrentAvailable && firstAvailable !== activeTab) {
      setActiveTab(firstAvailable);
    }
  }, [charts, activeTab, firstAvailable, availableCharts]);

  return (
    <Card className="border-muted" data-testid="card-tabbed-charts">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
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
              <CardContent className="pt-6 pb-8">
                <div className="flex flex-col items-center gap-4">
                  <div className="text-center mb-2">
                    <h3 className="text-lg font-semibold">{info.title}</h3>
                    <p className="text-sm text-muted-foreground">{info.purpose}</p>
                  </div>
                  <SouthIndianChart
                    lagna={data.lagna}
                    planets={data.planets}
                    dignity={data.dignity}
                    size={360}
                    title={info.title}
                    subtitle={info.subtitle}
                  />
                </div>
              </CardContent>
            </TabsContent>
          );
        })}
      </Tabs>
    </Card>
  );
}

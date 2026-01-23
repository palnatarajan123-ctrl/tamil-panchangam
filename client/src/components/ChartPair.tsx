import { SouthIndianChart } from "@/components/south-indian-chart";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ChartData {
  lagna: number;
  planets: Record<string, number>;
  dignity?: Record<string, "exalted" | "debilitated" | "neutral">;
}

interface ChartPairProps {
  d1: ChartData;
  d9: ChartData;
}

export function ChartPair({ d1, d9 }: ChartPairProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* ================= D1 ================= */}
      <Card className="border-muted">
        <CardHeader>
          <CardTitle>Rāsi Chart (D1)</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-6">
          <SouthIndianChart
            lagna={d1.lagna}
            planets={d1.planets}
            dignity={d1.dignity}
            size={360}
            title="Rāsi Chart (D1)"
            subtitle="South Indian"
          />
        </CardContent>
      </Card>

      {/* ================= D9 ================= */}
      <Card className="border-muted">
        <CardHeader>
          <CardTitle>Navamsa Chart (D9)</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-6">
          <SouthIndianChart
            lagna={d9.lagna}
            planets={d9.planets}
            dignity={d9.dignity}
            size={360}
            title="Navamsa Chart (D9)"
            subtitle="D9 · Marriage & Dharma"
          />
        </CardContent>
      </Card>
    </div>
  );
}

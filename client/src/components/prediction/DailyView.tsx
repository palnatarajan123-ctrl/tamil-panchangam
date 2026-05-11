import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  AlertTriangle,
  Sun,
  Moon,
  Star,
  Clock,
  Sunrise,
  Sunset,
} from "lucide-react";

interface DailyData {
  date: string;
  sunrise: string;
  sunset: string;
  rahu_kaalam: { start: string; end: string };
  yamagandam: { start: string; end: string };
  gulika_kaalam: { start: string; end: string };
  nakshatra: { name: string; index: number; pada: number; longitude_deg: number };
  tara_bala: { key: string; name: string; quality: string; distance: number };
  tithi: { name: string; paksha: string; number: number };
}

const TARA_QUALITY_COLOR: Record<string, string> = {
  favorable: "text-green-700 dark:text-green-400",
  neutral: "text-amber-700 dark:text-amber-400",
  challenging: "text-red-700 dark:text-red-400",
};

const TARA_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive"> = {
  favorable: "default",
  neutral: "secondary",
  challenging: "destructive",
};

function TimeWindow({
  label,
  start,
  end,
  description,
}: {
  label: string;
  start: string;
  end: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-md bg-red-50 dark:bg-red-950/20 border border-red-200/40 dark:border-red-800/30">
      <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-sm font-mono text-red-700 dark:text-red-300">
          {start} – {end}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
    </div>
  );
}

interface DailyViewProps {
  baseChartId: string;
  date?: string;
}

export function DailyView({ baseChartId, date }: DailyViewProps) {
  const dateParam = date ?? new Date().toISOString().split("T")[0];
  const params = new URLSearchParams({ base_chart_id: baseChartId, date: dateParam });

  const { data, isLoading, error } = useQuery<DailyData>({
    queryKey: ["daily", baseChartId, dateParam],
    queryFn: async () => {
      const res = await fetch(`/api/prediction/daily?${params}`);
      if (!res.ok) throw new Error("Failed to load daily data");
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        Loading daily Panchangam…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12 text-red-600 dark:text-red-400 text-sm">
        Could not load daily data. Please try again.
      </div>
    );
  }

  const formattedDate = new Date(data.date + "T00:00:00").toLocaleDateString(
    "en-IN",
    { weekday: "long", year: "numeric", month: "long", day: "numeric" }
  );

  return (
    <div className="space-y-6">
      {/* Date + Sunrise/Sunset */}
      <Card data-testid="card-daily-header">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-amber-500" />
            {formattedDate}
          </CardTitle>
          <CardDescription>
            Daily Panchangam · Inauspicious Windows
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-6 text-sm">
            <div className="flex items-center gap-2">
              <Sunrise className="h-4 w-4 text-amber-500" />
              <span className="text-muted-foreground">Sunrise</span>
              <span className="font-mono font-medium">{data.sunrise}</span>
            </div>
            <div className="flex items-center gap-2">
              <Sunset className="h-4 w-4 text-orange-500" />
              <span className="text-muted-foreground">Sunset</span>
              <span className="font-mono font-medium">{data.sunset}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Inauspicious Windows */}
      <Card data-testid="card-inauspicious-windows">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-red-500" />
            Inauspicious Windows
          </CardTitle>
          <CardDescription>
            Avoid starting new ventures or important activities during these times
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <TimeWindow
            label="Rahu Kaalam"
            start={data.rahu_kaalam.start}
            end={data.rahu_kaalam.end}
            description="Inauspicious period ruled by Rahu — avoid new beginnings"
          />
          <TimeWindow
            label="Yamagandam"
            start={data.yamagandam.start}
            end={data.yamagandam.end}
            description="Ruled by Yama — inauspicious for travel and legal matters"
          />
          <TimeWindow
            label="Gulika Kaalam"
            start={data.gulika_kaalam.start}
            end={data.gulika_kaalam.end}
            description="Ruled by Gulika (Saturn's shadow) — unfavorable for important tasks"
          />
        </CardContent>
      </Card>

      {/* Nakshatra + Tara Bala */}
      <Card data-testid="card-nakshatra-tara">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5 text-indigo-500" />
            Today's Moon
          </CardTitle>
          <CardDescription>
            Current nakshatra and its relationship to your birth star
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Moon Nakshatra
              </p>
              <p className="text-lg font-semibold">{data.nakshatra.name}</p>
              <p className="text-xs text-muted-foreground">
                Pada {data.nakshatra.pada} · {data.nakshatra.longitude_deg.toFixed(2)}°
              </p>
            </div>
          </div>

          <Separator />

          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Tara Bala
            </p>
            <div className="flex items-center gap-3">
              <Badge variant={TARA_BADGE_VARIANT[data.tara_bala.quality] ?? "secondary"}>
                {data.tara_bala.name}
              </Badge>
              <span className={`text-sm font-medium ${TARA_QUALITY_COLOR[data.tara_bala.quality] ?? ""}`}>
                {data.tara_bala.quality.charAt(0).toUpperCase() + data.tara_bala.quality.slice(1)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.tara_bala.distance} nakshatras from birth star
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Tithi */}
      <Card data-testid="card-tithi">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Moon className="h-5 w-5 text-sky-500" />
            Tithi (Lunar Day)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div>
              <p className="text-lg font-semibold">{data.tithi.name}</p>
              <p className="text-sm text-muted-foreground">
                {data.tithi.paksha} Paksha · Tithi {data.tithi.number}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

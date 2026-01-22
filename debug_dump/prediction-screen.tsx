import { useParams } from "wouter";
import { useState } from "react";
import { usePrediction } from "@/hooks/usePrediction";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { LifeAreaGrid } from "@/components/prediction/LifeAreaGrid";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";

type PeriodMode = "monthly" | "weekly" | "yearly";

export default function PredictionScreen() {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return <div className="text-red-600">Missing base chart id</div>;
  }

  const now = new Date();

  const [mode, setMode] = useState<PeriodMode>("monthly");
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [week, setWeek] = useState(1);

  const { data, isLoading, error } = usePrediction({
    baseChartId: id,
    period: mode,
    year,
    month: mode === "monthly" ? month : undefined,
    week: mode === "weekly" ? week : undefined,
  });

  return (
    <div className="space-y-6">
      {/* -----------------------------
          Header + Period Controls
         ----------------------------- */}
      <header className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Predictions</h1>

          {/* Period Mode Selector */}
          <div className="flex gap-2">
            {(["monthly", "weekly", "yearly"] as PeriodMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1 rounded text-sm border transition ${
                  mode === m
                    ? "bg-primary text-primary-foreground"
                    : "bg-background text-foreground"
                }`}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Time Selectors */}
        <div className="flex gap-2">
          {/* Month selector */}
          {mode === "monthly" && (
            <Select
              value={String(month)}
              onValueChange={(v) => setMonth(Number(v))}
            >
              <SelectTrigger className="w-[110px]">
                <SelectValue placeholder="Month" />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 12 }).map((_, i) => (
                  <SelectItem key={i + 1} value={String(i + 1)}>
                    {new Date(0, i).toLocaleString("default", {
                      month: "short",
                    })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Week selector */}
          {mode === "weekly" && (
            <Select
              value={String(week)}
              onValueChange={(v) => setWeek(Number(v))}
            >
              <SelectTrigger className="w-[110px]">
                <SelectValue placeholder="Week" />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 53 }).map((_, i) => (
                  <SelectItem key={i + 1} value={String(i + 1)}>
                    Week {i + 1}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Year selector */}
          <Select
            value={String(year)}
            onValueChange={(v) => setYear(Number(v))}
          >
            <SelectTrigger className="w-[90px]">
              <SelectValue placeholder="Year" />
            </SelectTrigger>
            <SelectContent>
              {[year - 1, year, year + 1].map((y) => (
                <SelectItem key={y} value={String(y)}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      {/* -----------------------------
          States
         ----------------------------- */}
      {isLoading && <div>Computing prediction…</div>}

      {error && (
        <div className="text-red-600">
          Prediction failed. Please try again.
        </div>
      )}

      {/* -----------------------------
          Prediction Output
         ----------------------------- */}
      {data && (
        <>
          <LifeAreaGrid lifeAreas={data.details.synthesis.life_areas} />
          <ExplainabilityDrawer explainability={data.explainability} />
        </>
      )}
    </div>
  );
}

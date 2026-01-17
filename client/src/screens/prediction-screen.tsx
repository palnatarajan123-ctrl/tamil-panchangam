// client/src/screens/prediction-screen.tsx

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

import { TimelineBar } from "@/components/prediction/timeline-bar";

export default function PredictionScreen() {
  const { id } = useParams<{ id: string }>();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const timeframe = {
    mode: "monthly",
    year,
    month,
  };

  const { data, isLoading, error } = usePrediction(id!, timeframe);

  return (
    <div className="space-y-6">
      {/* -----------------------------
          Header + Period Selector
         ----------------------------- */}
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Predictions</h1>

        <div className="flex gap-2">
          <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
            <SelectTrigger className="w-[110px]">
              <SelectValue placeholder="Month" />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: 12 }).map((_, i) => (
                <SelectItem key={i + 1} value={String(i + 1)}>
                  {new Date(0, i).toLocaleString("default", { month: "short" })}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
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
      {error && <div className="text-red-600">Prediction failed.</div>}

      {data && (
        <>
          <ConfidenceBlock confidence={data.explainability} />
          <TimelineBar timeline={data.details.synthesis.life_areas} />
        </>
      )}
    </div>
  );
}

/* ---------------------------------
   Confidence (EPIC-8)
---------------------------------- */

function ConfidenceBlock({ confidence }: any) {
  return (
    <div className="rounded-lg border p-4">
      <div className="font-medium">Confidence</div>
      <div className="text-sm text-muted-foreground">
        {confidence.reason}
      </div>
    </div>
  );
}

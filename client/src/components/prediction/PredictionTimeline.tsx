import { cn } from "@/lib/utils";

interface TimelineMonth {
  year: number;
  month: number; // 1–12
  score?: number;
  tone?: "Strong" | "Supportive" | "Mixed" | "Challenging";
  available: boolean;
}

interface Props {
  months: TimelineMonth[];
  selectedYear: number;
  selectedMonth: number;
  onSelect: (year: number, month: number) => void;
}

const MONTH_LABELS = [
  "Jan","Feb","Mar","Apr","May","Jun",
  "Jul","Aug","Sep","Oct","Nov","Dec"
];

export function PredictionTimeline({
  months,
  selectedYear,
  selectedMonth,
  onSelect,
}: Props) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {months.map((m) => {
        const selected =
          m.year === selectedYear && m.month === selectedMonth;

        return (
          <button
            key={`${m.year}-${m.month}`}
            disabled={!m.available}
            onClick={() => onSelect(m.year, m.month)}
            className={cn(
              "min-w-[80px] rounded-md border px-3 py-2 text-sm text-center transition",
              m.available
                ? "hover:bg-muted"
                : "opacity-40 cursor-not-allowed",
              selected
                ? "border-primary bg-primary/10"
                : "border-border"
            )}
          >
            <div className="font-medium">
              {MONTH_LABELS[m.month - 1]}
            </div>
            <div className="text-xs text-muted-foreground">
              {m.year}
            </div>

            {m.score !== undefined && (
              <div className="mt-1 text-xs font-medium">
                {m.score} · {m.tone}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

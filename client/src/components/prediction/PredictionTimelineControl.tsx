import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

type Period = "weekly" | "monthly" | "yearly";

interface Props {
  period: Period;
  year: number;
  index: number;
  onChange: (next: { year: number; index: number }) => void;
}

export function PredictionTimelineControl({
  period,
  year,
  index,
  onChange,
}: Props) {
  const maxIndex =
    period === "weekly" ? 53 :
    period === "monthly" ? 12 :
    1;

  function go(delta: number) {
    let nextIndex = index + delta;
    let nextYear = year;

    if (nextIndex < 1) {
      nextYear -= 1;
      nextIndex = maxIndex;
    }

    if (nextIndex > maxIndex) {
      nextYear += 1;
      nextIndex = 1;
    }

    onChange({ year: nextYear, index: nextIndex });
  }

  const label =
    period === "weekly"
      ? `Week ${index}, ${year}`
      : period === "monthly"
      ? `${new Date(0, index - 1).toLocaleString("default", { month: "long" })} ${year}`
      : `${year}`;

  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" size="icon" onClick={() => go(-1)}>
        <ChevronLeft className="h-4 w-4" />
      </Button>

      <div className="min-w-[180px] text-center font-medium">
        {label}
      </div>

      <Button variant="outline" size="icon" onClick={() => go(1)}>
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

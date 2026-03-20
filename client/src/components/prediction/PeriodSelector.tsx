import { Button } from "@/components/ui/button";
import { PeriodType } from "@/types/prediction";

const periods: PeriodType[] = ["monthly", "yearly"];

export function PeriodSelector({
  value,
  onChange,
}: {
  value: PeriodType;
  onChange: (p: PeriodType) => void;
}) {
  return (
    <div className="flex gap-2">
      {periods.map((p) => (
        <Button
          key={p}
          variant={p === value ? "default" : "outline"}
          onClick={() => onChange(p)}
        >
          {p.charAt(0).toUpperCase() + p.slice(1)}
        </Button>
      ))}
    </div>
  );
}

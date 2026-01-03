import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: "ok" | "stub" | "error" | "loading";
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const statusConfig = {
    ok: {
      variant: "default" as const,
      dotColor: "bg-green-500",
      text: label || "Operational",
    },
    stub: {
      variant: "secondary" as const,
      dotColor: "bg-amber-500",
      text: label || "Pending Implementation",
    },
    error: {
      variant: "destructive" as const,
      dotColor: "bg-red-500",
      text: label || "Error",
    },
    loading: {
      variant: "outline" as const,
      dotColor: "bg-blue-500 animate-pulse",
      text: label || "Loading...",
    },
  };

  const config = statusConfig[status];

  return (
    <Badge variant={config.variant} className={cn("gap-1.5", className)} data-testid={`badge-status-${status}`}>
      <span className={cn("w-1.5 h-1.5 rounded-full", config.dotColor)} />
      {config.text}
    </Badge>
  );
}

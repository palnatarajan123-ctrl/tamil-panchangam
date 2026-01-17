import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "./status-badge";
import { Clock, MapPin, User, ExternalLink } from "lucide-react";

/**
 * Lightweight chart summary returned by /api/base-chart/list
 */
interface ChartSummary {
  id: string;
  checksum: string;
  locked: boolean;
}

/**
 * Backend response shape
 */
interface ChartListResponse {
  count: number;
  charts: {
    base_chart_id: string;
    checksum: string;
    locked: boolean;
  }[];
}

interface ChartListProps {
  onViewChart?: (chartId: string) => void;
}

export function ChartList({ onViewChart }: ChartListProps) {
  const { data, isLoading, error } = useQuery<ChartListResponse>({
    queryKey: ["/api/base-chart/list"],
  });

  // --------------------------------
  // Normalize backend response
  // --------------------------------
  const charts: ChartSummary[] =
    Array.isArray(data?.charts)
      ? data.charts
          .filter((c) => !!c?.base_chart_id)
          .map((c) => ({
            id: c.base_chart_id,
            checksum: c.checksum,
            locked: c.locked,
          }))
      : [];

  // --------------------------------
  // Loading state
  // --------------------------------
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // --------------------------------
  // Error state
  // --------------------------------
  if (error) {
    console.error("[ChartList] Failed to load charts:", error);
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Failed to load charts
        </CardContent>
      </Card>
    );
  }

  // --------------------------------
  // Empty state
  // --------------------------------
  if (charts.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="space-y-2">
            <p className="text-muted-foreground">
              No birth charts generated yet
            </p>
            <p className="text-sm text-muted-foreground">
              Create your first chart using the form above
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // --------------------------------
  // Render chart summaries
  // --------------------------------
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        Saved Charts
        <span className="text-sm font-normal text-muted-foreground">
          ({charts.length})
        </span>
      </h3>

      {charts.map((chart) => (
        <Card key={chart.id} className="hover-elevate transition-all">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  Birth Chart
                </CardTitle>

                <CardDescription className="mt-1">
                  Immutable Tamil Panchangam chart
                </CardDescription>
              </div>

              <StatusBadge status={chart.locked ? "ok" : "stub"} />
            </div>
          </CardHeader>

          <CardContent className="pt-0">
            <div className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground font-mono">
                ID: {chart.id.slice(0, 8)}…
              </div>

              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => onViewChart?.(chart.id)}
                data-testid={`button-view-chart-${chart.id}`}
              >
                <ExternalLink className="h-3 w-3" />
                View Chart
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

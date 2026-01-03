import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "./status-badge";
import { Clock, MapPin, User, ExternalLink } from "lucide-react";
import type { BaseChart } from "@shared/schema";

interface ChartListProps {
  onViewChart?: (chartId: string) => void;
}

export function ChartList({ onViewChart }: ChartListProps) {
  const { data: charts, isLoading, error } = useQuery<BaseChart[]>({
    queryKey: ["/api/base-chart/list"],
  });

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

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Failed to load charts</p>
        </CardContent>
      </Card>
    );
  }

  if (!charts || charts.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="space-y-2">
            <p className="text-muted-foreground">No birth charts generated yet</p>
            <p className="text-sm text-muted-foreground">
              Create your first chart using the form above
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

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
                  {chart.name}
                </CardTitle>
                <CardDescription className="flex items-center gap-4 mt-1 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {chart.date_of_birth} at {chart.time_of_birth}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {chart.place_of_birth}
                  </span>
                </CardDescription>
              </div>
              <StatusBadge status={chart.status === "stub" ? "stub" : "ok"} />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground font-mono">
                ID: {chart.id.substring(0, 8)}...
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

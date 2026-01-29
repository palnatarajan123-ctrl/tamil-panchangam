import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { 
  Settings, 
  Activity, 
  Zap, 
  AlertCircle,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle
} from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface LLMStatus {
  llm_enabled: boolean;
  active_provider: string;
  provider_available: boolean;
  current_prompt_version: string;
  monthly_budget: number;
}

interface MonthlyUsage {
  budget: number;
  used: number;
  remaining: number;
  percent_used: number;
}

interface RecentCall {
  id: string;
  base_chart_id: string;
  period_type: string;
  period_key: string;
  total_tokens: number | null;
  fallback_reason: string | null;
  created_at: string;
}

interface FallbackSummary {
  reason: string;
  count: number;
}

export default function AdminLLM() {
  const { data: status, isLoading: statusLoading } = useQuery<LLMStatus>({
    queryKey: ["/api/admin/llm/status"],
    refetchInterval: 30000,
  });

  const { data: usage, isLoading: usageLoading } = useQuery<MonthlyUsage>({
    queryKey: ["/api/admin/llm/usage/monthly"],
    refetchInterval: 30000,
  });

  const { data: recentCalls, isLoading: callsLoading } = useQuery<RecentCall[]>({
    queryKey: ["/api/admin/llm/usage/recent"],
  });

  const { data: fallbackSummary } = useQuery<FallbackSummary[]>({
    queryKey: ["/api/admin/llm/fallback-summary"],
  });

  const toggleMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const res = await apiRequest("POST", "/api/admin/llm/toggle", { enabled });
      if (!res.ok) throw new Error("Failed to toggle LLM");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/admin/llm/status"] });
    },
  });

  const getUsageColor = (percent: number) => {
    if (percent >= 90) return "text-red-500";
    if (percent >= 70) return "text-amber-500";
    return "text-green-500";
  };

  return (
    <div className="container max-w-6xl mx-auto px-4 py-8">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-serif font-bold flex items-center gap-3" data-testid="heading-admin-llm">
          <Settings className="h-8 w-8 text-primary" />
          AI / LLM Usage Dashboard
        </h1>
        <p className="text-muted-foreground">
          Monitor and manage LLM interpretation usage for astrology predictions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <Card data-testid="card-llm-status">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              LLM Status
            </CardTitle>
            <CardDescription>Current configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {statusLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">LLM Enabled</span>
                  <Switch
                    checked={status?.llm_enabled ?? false}
                    onCheckedChange={(checked) => toggleMutation.mutate(checked)}
                    disabled={toggleMutation.isPending}
                    data-testid="switch-llm-enabled"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Active Provider</span>
                  <Badge variant={status?.provider_available ? "default" : "secondary"}>
                    {status?.active_provider || "None"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Provider Available</span>
                  {status?.provider_available ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Prompt Version</span>
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {status?.current_prompt_version}
                  </code>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-monthly-usage">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Monthly Token Usage
            </CardTitle>
            <CardDescription>Current month consumption</CardDescription>
          </CardHeader>
          <CardContent>
            {usageLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : usage ? (
              <div className="space-y-4">
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getUsageColor(usage.percent_used)}`}>
                    {usage.percent_used.toFixed(1)}%
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    of monthly budget used
                  </div>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      usage.percent_used >= 90 ? "bg-red-500" :
                      usage.percent_used >= 70 ? "bg-amber-500" : "bg-green-500"
                    }`}
                    style={{ width: `${Math.min(100, usage.percent_used)}%` }}
                  />
                </div>
                <div className="grid grid-cols-3 text-center text-sm">
                  <div>
                    <div className="font-semibold">{usage.used.toLocaleString()}</div>
                    <div className="text-muted-foreground">Used</div>
                  </div>
                  <div>
                    <div className="font-semibold">{usage.remaining.toLocaleString()}</div>
                    <div className="text-muted-foreground">Remaining</div>
                  </div>
                  <div>
                    <div className="font-semibold">{usage.budget.toLocaleString()}</div>
                    <div className="text-muted-foreground">Budget</div>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card data-testid="card-fallback-summary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Fallback Summary
            </CardTitle>
            <CardDescription>This month's fallback reasons</CardDescription>
          </CardHeader>
          <CardContent>
            {fallbackSummary && fallbackSummary.length > 0 ? (
              <div className="space-y-2">
                {fallbackSummary.map((item) => (
                  <div key={item.reason} className="flex items-center justify-between">
                    <span className="text-sm truncate max-w-[150px]" title={item.reason}>
                      {item.reason === "success" ? (
                        <span className="text-green-600">Success</span>
                      ) : (
                        item.reason
                      )}
                    </span>
                    <Badge variant={item.reason === "success" ? "default" : "secondary"}>
                      {item.count}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-4">
                No calls this month
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card data-testid="card-recent-calls">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Recent LLM Calls
          </CardTitle>
          <CardDescription>Last 20 interpretation requests</CardDescription>
        </CardHeader>
        <CardContent>
          {callsLoading ? (
            <Skeleton className="h-48 w-full" />
          ) : recentCalls && recentCalls.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3">Timestamp</th>
                    <th className="text-left py-2 px-3">Chart ID</th>
                    <th className="text-left py-2 px-3">Period</th>
                    <th className="text-right py-2 px-3">Tokens</th>
                    <th className="text-left py-2 px-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentCalls.map((call) => (
                    <tr key={call.id} className="border-b last:border-0">
                      <td className="py-2 px-3 text-muted-foreground">
                        {new Date(call.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 px-3">
                        <code className="text-xs bg-muted px-1 rounded">
                          {call.base_chart_id.slice(0, 8)}...
                        </code>
                      </td>
                      <td className="py-2 px-3">
                        {call.period_type} / {call.period_key}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {call.total_tokens?.toLocaleString() ?? "-"}
                      </td>
                      <td className="py-2 px-3">
                        {call.fallback_reason ? (
                          <Badge variant="secondary" className="text-xs">
                            {call.fallback_reason}
                          </Badge>
                        ) : (
                          <Badge variant="default" className="text-xs">
                            Success
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No LLM calls recorded yet
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

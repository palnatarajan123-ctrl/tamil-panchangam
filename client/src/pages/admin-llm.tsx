import { useEffect, useState, useCallback } from "react";
import { apiRequest, queryClient } from "@/lib/queryClient";

// ── Types ──────────────────────────────────────────────────────────────
interface LLMSummary {
  spend_mtd: number;
  budget: number;
  pct_used: number;
  remaining: number;
  total_tokens_mtd: number;
  total_calls: number;
  days_elapsed: number;
  days_in_month: number;
  days_remaining: number;
  burn_rate_per_day: number;
  forecast_eom: number;
  will_exceed_budget: boolean;
  llm_enabled: boolean;
  paused_reason: string | null;
  auto_pause_enabled: boolean;
  auto_pause_threshold_pct: number;
  breakdown: Record<string, { calls: number; cost_usd: number }>;
  fallbacks: Record<string, number>;
}

interface LLMCall {
  id: string;
  chart_id: string;
  call_type: "prediction" | "chat";
  period: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  status: string;
  fallback_reason: string | null;
  created_at: string;
}

// ── Helpers ────────────────────────────────────────────────────────────
const fmt$ = (n: number) => `$${n.toFixed(4)}`;
const fmtK = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);

// ── Main component ─────────────────────────────────────────────────────
export default function AdminLLM() {
  const [summary, setSummary] = useState<LLMSummary | null>(null);
  const [calls, setCalls] = useState<LLMCall[]>([]);
  const [totalCalls, setTotalCalls] = useState(0);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // Budget edit state
  const [editBudget, setEditBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState("");
  const [thresholdInput, setThresholdInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, callsRes] = await Promise.all([
        fetch("/api/admin/llm/summary"),
        fetch(`/api/admin/llm/calls?page=${page}&per_page=20${typeFilter ? `&call_type=${typeFilter}` : ""}`),
      ]);
      const sum: LLMSummary = await sumRes.json();
      const callData = await callsRes.json();
      setSummary(sum);
      setCalls(callData.calls);
      setTotalCalls(callData.total);
      setBudgetInput(String(sum.budget));
      setThresholdInput(String(sum.auto_pause_threshold_pct));
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter]);

  useEffect(() => { load(); }, [load]);

  const saveBudget = async () => {
    await fetch("/api/admin/llm/budget", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        monthly_budget_usd: parseFloat(budgetInput),
        auto_pause_threshold_pct: parseInt(thresholdInput),
      }),
    });
    setEditBudget(false);
    load();
  };

  const toggleLLM = async (enabled: boolean) => {
    await apiRequest("POST", "/api/admin/llm/toggle", { enabled });
    queryClient.invalidateQueries({ queryKey: ["/api/admin/llm/status"] });
    load();
  };

  if (!summary) return <div className="p-8 text-muted-foreground">Loading...</div>;

  const barPct = Math.min(summary.pct_used, 100);
  const barColor = summary.pct_used >= 90 ? "bg-red-500"
    : summary.pct_used >= 70 ? "bg-yellow-500"
      : "bg-green-500";

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">

      {/* ── Header ── */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3" data-testid="heading-admin-llm">
          <span className="text-primary">⚙</span> AI / LLM Usage Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Monitor spend, control budget, and manage LLM access across predictions and chat.
        </p>
      </div>

      {/* ── Auto-pause warning banner ── */}
      {!summary.llm_enabled && (
        <div className="bg-destructive/10 border border-destructive rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-destructive font-semibold">
              ⚠ LLM Paused
              {summary.paused_reason === "budget_exceeded"
                ? " — Monthly budget threshold reached"
                : " — Manually disabled"}
            </p>
            <p className="text-muted-foreground text-sm mt-1">
              {fmt$(summary.spend_mtd)} of {fmt$(summary.budget)} used this month.
              Re-enable manually or increase budget.
            </p>
          </div>
          <button
            onClick={() => toggleLLM(true)}
            className="bg-primary hover:opacity-90 text-primary-foreground px-4 py-2 rounded-lg font-medium text-sm"
          >
            Resume LLM
          </button>
        </div>
      )}

      {/* ── Zone 1: Control Bar ── */}
      <div className="bg-card rounded-xl p-5 flex flex-wrap items-center gap-6 border border-border">
        {/* Toggle */}
        <div className="flex items-center gap-3">
          <span className="text-foreground font-medium text-sm">LLM</span>
          <button
            onClick={() => toggleLLM(!summary.llm_enabled)}
            className={`relative w-12 h-6 rounded-full transition-colors ${summary.llm_enabled ? "bg-primary" : "bg-muted"}`}
          >
            <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${summary.llm_enabled ? "left-7" : "left-1"}`} />
          </button>
          <span className={`text-sm font-medium ${summary.llm_enabled ? "text-green-500" : "text-destructive"}`}>
            {summary.llm_enabled ? "Active" : "Paused"}
          </span>
        </div>

        <div className="h-8 w-px bg-border" />

        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm">Provider</span>
          <span className="bg-primary text-primary-foreground text-xs font-bold px-2 py-1 rounded">anthropic</span>
          <span className="bg-muted text-muted-foreground text-xs px-2 py-1 rounded">claude-sonnet-4-6</span>
        </div>

        <div className="h-8 w-px bg-border" />

        {editBudget ? (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-muted-foreground text-sm">Budget $</span>
            <input
              value={budgetInput}
              onChange={e => setBudgetInput(e.target.value)}
              className="w-20 bg-background border border-input rounded px-2 py-1 text-foreground text-sm"
            />
            <span className="text-muted-foreground text-sm">Auto-pause at</span>
            <input
              value={thresholdInput}
              onChange={e => setThresholdInput(e.target.value)}
              className="w-16 bg-background border border-input rounded px-2 py-1 text-foreground text-sm"
            />
            <span className="text-muted-foreground text-sm">%</span>
            <button onClick={saveBudget} className="bg-primary text-primary-foreground text-sm px-3 py-1 rounded">Save</button>
            <button onClick={() => setEditBudget(false)} className="text-muted-foreground text-sm px-2 py-1">Cancel</button>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Budget:</span>
            <span className="text-foreground font-medium">{fmt$(summary.budget)}/mo</span>
            <span className="text-muted-foreground ml-2">Auto-pause at:</span>
            <span className="text-foreground font-medium">{summary.auto_pause_threshold_pct}%</span>
            <button
              onClick={() => setEditBudget(true)}
              className="text-primary hover:opacity-80 text-xs ml-1"
            >✎ Edit</button>
          </div>
        )}
      </div>

      {/* ── Zone 2: Three Metric Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* Card 1: Monthly Spend */}
        <div className="bg-card rounded-xl p-5 border border-border" data-testid="card-monthly-usage">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-muted-foreground">↗</span>
            <span className="font-semibold text-foreground">Monthly Spend</span>
          </div>
          <div className={`text-4xl font-bold ${summary.pct_used >= 90 ? "text-red-500" : summary.pct_used >= 70 ? "text-yellow-500" : "text-green-500"}`}>
            {summary.pct_used}%
          </div>
          <div className="text-muted-foreground text-sm mb-3">of {fmt$(summary.budget)} budget used</div>
          <div className="w-full bg-muted rounded-full h-2 mb-3">
            <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${barPct}%` }} />
          </div>
          <div className="flex justify-between text-sm">
            <div>
              <div className="text-foreground font-medium">{fmt$(summary.spend_mtd)}</div>
              <div className="text-muted-foreground">Used</div>
            </div>
            <div className="text-center">
              <div className="text-foreground font-medium">{fmt$(summary.remaining)}</div>
              <div className="text-muted-foreground">Remaining</div>
            </div>
            <div className="text-right">
              <div className="text-foreground font-medium">{fmt$(summary.budget)}</div>
              <div className="text-muted-foreground">Budget</div>
            </div>
          </div>
        </div>

        {/* Card 2: Calls by Type */}
        <div className="bg-card rounded-xl p-5 border border-border" data-testid="card-fallback-summary">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-muted-foreground">⊙</span>
            <span className="font-semibold text-foreground">Calls by Type</span>
            <span className="text-muted-foreground text-xs ml-auto">{summary.total_calls} total</span>
          </div>

          {(["prediction", "chat"] as const).map(type => {
            const d = summary.breakdown[type];
            return (
              <div key={type} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${type === "chat" ? "bg-blue-500/20 text-blue-400" : "bg-primary/20 text-primary"}`}>
                    {type}
                  </span>
                  <span className="text-muted-foreground text-sm">{d ? `${d.calls} calls` : "No data"}</span>
                </div>
                <span className="text-foreground font-medium text-sm">{d ? fmt$(d.cost_usd) : "—"}</span>
              </div>
            );
          })}

          <div className="mt-3 pt-2 border-t border-border">
            <p className="text-muted-foreground text-xs mb-1">Fallback reasons</p>
            {Object.entries(summary.fallbacks).slice(0, 4).map(([reason, count]) => (
              <div key={reason} className="flex justify-between text-xs mt-1">
                <span className={reason === "success" ? "text-green-500" : "text-muted-foreground"}>{reason}</span>
                <span className={`px-1.5 py-0.5 rounded font-medium ${reason === "success" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Card 3: Forecast */}
        <div className="bg-card rounded-xl p-5 border border-border">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-muted-foreground">⊙</span>
            <span className="font-semibold text-foreground">Forecast</span>
          </div>
          <div className={`text-4xl font-bold ${summary.will_exceed_budget ? "text-red-500" : "text-green-500"}`}>
            {fmt$(summary.forecast_eom)}
          </div>
          <div className="text-muted-foreground text-sm mb-4">projected end-of-month</div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Burn rate</span>
              <span className="text-foreground">{fmt$(summary.burn_rate_per_day)}/day</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Days elapsed</span>
              <span className="text-foreground">{summary.days_elapsed} / {summary.days_in_month}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Days remaining</span>
              <span className="text-foreground">{summary.days_remaining}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tokens used</span>
              <span className="text-foreground">{fmtK(summary.total_tokens_mtd)}</span>
            </div>
          </div>

          <div className={`mt-4 text-xs px-3 py-2 rounded-lg font-medium ${summary.will_exceed_budget ? "bg-destructive/10 text-destructive" : "bg-green-500/10 text-green-500"}`}>
            {summary.will_exceed_budget
              ? `⚠ Will exceed budget by ${fmt$(summary.forecast_eom - summary.budget)}`
              : `✓ Within budget — ${fmt$(summary.budget - summary.forecast_eom)} headroom`}
          </div>
        </div>
      </div>

      {/* ── Zone 3: Unified Call Log ── */}
      <div className="bg-card rounded-xl p-5 border border-border" data-testid="card-recent-calls">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <span className="text-muted-foreground">⊙</span> Recent LLM Calls
            </h2>
            <p className="text-muted-foreground text-sm">{totalCalls} total calls this month</p>
          </div>
          <div className="flex gap-2">
            {(["", "prediction", "chat"] as const).map(t => (
              <button
                key={t}
                onClick={() => { setTypeFilter(t); setPage(1); }}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium ${typeFilter === t ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground"}`}
              >
                {t === "" ? "All" : t}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted-foreground border-b border-border">
                <th className="text-left py-2 pr-4 font-medium">Timestamp</th>
                <th className="text-left py-2 pr-4 font-medium">Type</th>
                <th className="text-left py-2 pr-4 font-medium">Chart ID</th>
                <th className="text-left py-2 pr-4 font-medium">Period</th>
                <th className="text-right py-2 pr-4 font-medium">Input tok</th>
                <th className="text-right py-2 pr-4 font-medium">Output tok</th>
                <th className="text-right py-2 pr-4 font-medium">Cost</th>
                <th className="text-right py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {calls.map(call => (
                <tr key={call.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="py-2 pr-4 text-muted-foreground">
                    {new Date(call.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${call.call_type === "chat" ? "bg-blue-500/20 text-blue-400" : "bg-primary/20 text-primary"}`}>
                      {call.call_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">
                    {call.chart_id?.slice(0, 8)}...
                  </td>
                  <td className="py-2 pr-4 text-foreground">{call.period || "—"}</td>
                  <td className="py-2 pr-4 text-right text-muted-foreground">{fmtK(call.input_tokens)}</td>
                  <td className="py-2 pr-4 text-right text-muted-foreground">{fmtK(call.output_tokens)}</td>
                  <td className="py-2 pr-4 text-right text-foreground font-medium">{fmt$(call.cost_usd)}</td>
                  <td className="py-2 text-right">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${call.status === "success" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                      {call.status === "success" ? "Success" : call.fallback_reason || call.status}
                    </span>
                  </td>
                </tr>
              ))}
              {calls.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-muted-foreground">No LLM calls recorded yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex justify-between items-center mt-4 text-sm text-muted-foreground">
          <span>Showing {calls.length} of {totalCalls}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-muted rounded disabled:opacity-40"
            >← Prev</button>
            <span className="px-3 py-1">Page {page}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={calls.length < 20}
              className="px-3 py-1 bg-muted rounded disabled:opacity-40"
            >Next →</button>
          </div>
        </div>
      </div>

    </div>
  );
}

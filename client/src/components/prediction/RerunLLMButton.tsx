import { useState } from "react";
import { authHeaders } from "@/lib/auth";

interface RerunLLMButtonProps {
  baseChartId: string;
  periodType: "monthly" | "yearly";
  year: number;
  month?: number;
  onRerunComplete: () => void;
}

type Status = "idle" | "loading" | "success" | "error" | "rate_limited";

export function RerunLLMButton({
  baseChartId,
  periodType,
  year,
  month,
  onRerunComplete,
}: RerunLLMButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string>("");

  const handleRerun = async () => {
    if (status === "loading") return;

    const periodLabel =
      periodType === "monthly" && month
        ? `${year}-${String(month).padStart(2, "0")}`
        : String(year);

    const confirmed = window.confirm(
      `Rerun LLM interpretation for ${periodLabel}?\n\nThis will generate fresh AI interpretation using v6.`
    );
    if (!confirmed) return;

    setStatus("loading");
    setMessage("");

    try {
      const params = new URLSearchParams({
        period_type: periodType,
        year: String(year),
        ...(month ? { month: String(month) } : {}),
      });

      const response = await fetch(
        `/api/prediction/rerun-llm/${baseChartId}?${params}`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const data = await response.json();

      if (response.status === 429) {
        setStatus("rate_limited");
        setMessage("Already rerun in last 24h");
        setTimeout(() => {
          setStatus("idle");
          setMessage("");
        }, 4000);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Rerun failed");
      }

      setStatus("success");
      setMessage("Cache cleared — refreshing...");

      setTimeout(() => {
        onRerunComplete();
        setStatus("idle");
        setMessage("");
      }, 1500);
    } catch (e: any) {
      setStatus("error");
      setMessage(e.message || "Rerun failed");
      setTimeout(() => {
        setStatus("idle");
        setMessage("");
      }, 3000);
    }
  };

  const buttonStyle: Record<Status, string> = {
    idle: "border-border text-muted-foreground hover:text-foreground hover:border-primary/50",
    loading: "border-border text-muted-foreground cursor-not-allowed",
    success: "border-green-700 text-green-400",
    error: "border-red-700 text-red-400",
    rate_limited: "border-amber-700 text-amber-400",
  };

  const messageColor: Record<Status, string> = {
    idle: "",
    loading: "text-muted-foreground",
    success: "text-green-400",
    error: "text-red-400",
    rate_limited: "text-amber-400",
  };

  return (
    <div className="flex items-center gap-2">
      {message && (
        <span className={`text-xs ${messageColor[status]}`}>{message}</span>
      )}
      <button
        onClick={handleRerun}
        disabled={status === "loading"}
        className={`text-xs px-3 py-1 rounded border transition-colors ${buttonStyle[status]}`}
        title="Admin: regenerate LLM interpretation with latest v6 prompt"
      >
        {status === "loading" ? (
          <span className="flex items-center gap-1">
            <span className="animate-spin inline-block">⟳</span>
            Clearing...
          </span>
        ) : (
          "⟳ Rerun LLM"
        )}
      </button>
    </div>
  );
}

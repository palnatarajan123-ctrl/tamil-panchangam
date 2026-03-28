// client/src/components/ChatPanel.tsx
import { useState, useRef, useEffect } from "react";
import { X, Send, MessageCircle, Sparkles } from "lucide-react";
import { useChat } from "@/hooks/useChat";

interface ChatPanelProps {
  baseChartId: string;
  chartName: string;
  mahadasha: string;
  antardasha: string;
  periodLabel: string;
  onClose: () => void;
}

export function ChatPanel({
  baseChartId,
  chartName,
  mahadasha,
  antardasha,
  periodLabel,
  onClose,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { messages, isStreaming, error, usage, sendMessage } = useChat(baseChartId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    await sendMessage(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    "Will I get a promotion this month?",
    "What to expect from relationships?",
    "Should I travel this period?",
    "What should I focus on for health?",
  ];

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-500" />
          <div>
            <p className="text-sm font-medium text-foreground">Ask Jyotishi</p>
            <p className="text-xs text-muted-foreground">
              {chartName} · {mahadasha}→{antardasha} · {periodLabel}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {usage && !usage.unlimited && (
            <span className="text-xs text-muted-foreground">
              {usage.remaining}/{usage.limit} left
            </span>
          )}
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground text-center pt-2">
              Ask anything about your chart and this period
            </p>
            <div className="space-y-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="w-full text-left text-xs px-3 py-2 rounded-lg border border-border hover:bg-accent hover:text-accent-foreground transition-colors text-muted-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-sm"
                  : "bg-muted text-foreground rounded-bl-sm"
              }`}
            >
              {msg.content}
              {msg.streaming && (
                <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current opacity-70 animate-pulse rounded-sm" />
              )}
            </div>
          </div>
        ))}

        {error && (
          <p className="text-xs text-destructive text-center px-2">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border bg-card">
        {usage && !usage.unlimited && usage.remaining === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-1">
            Monthly question limit reached. Resets next month.
          </p>
        ) : (
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your chart..."
              rows={1}
              disabled={isStreaming}
              className="flex-1 resize-none rounded-xl border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 max-h-24 overflow-y-auto"
              style={{ minHeight: "38px" }}
            />
            <button
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

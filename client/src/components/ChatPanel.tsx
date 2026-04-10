// client/src/components/ChatPanel.tsx
import { useState, useRef, useEffect } from "react";
import { X, Send, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChat } from "@/hooks/useChat";

interface ChatPanelProps {
  baseChartId: string;
  chartName: string;
  mahadasha: string;
  antardasha: string;
  periodLabel: string;
  onClose: () => void;
  chatEndpoint?: string;
  readingAsName?: string;
  contextType?: string;
  groupId?: string;
}

export function ChatPanel({
  baseChartId,
  chartName,
  mahadasha,
  antardasha,
  periodLabel,
  onClose,
  chatEndpoint = "/api/chat/stream",
  readingAsName,
  contextType,
  groupId,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { messages, isStreaming, error, usage, sendMessage } = useChat(baseChartId, chatEndpoint, readingAsName, contextType, groupId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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

  const headerSub = [chartName, mahadasha && antardasha ? `${mahadasha} → ${antardasha}` : null, periodLabel]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground leading-tight">Ask Jyotishi</p>
            <p className="text-xs text-muted-foreground truncate leading-tight">{headerSub}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {usage && !usage.unlimited && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {usage.remaining}/{usage.limit}
            </span>
          )}
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors p-0.5">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground text-center pt-1">
              Ask anything about your chart
            </p>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="w-full text-left text-xs px-2.5 py-1.5 rounded-lg border border-border hover:bg-accent transition-colors text-muted-foreground"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[88%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-amber-500 text-white rounded-br-sm"
                  : "bg-muted text-foreground rounded-bl-sm"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-strong:font-semibold">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.streaming && (
                    <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current opacity-70 animate-pulse rounded-sm" />
                  )}
                </div>
              ) : (
                <span>{msg.content}</span>
              )}
            </div>
          </div>
        ))}

        {error && <p className="text-xs text-destructive text-center">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-2.5 border-t border-border bg-card shrink-0">
        {usage && !usage.unlimited && usage.remaining === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-1">
            Monthly limit reached. Resets next month.
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
              style={{ minHeight: "36px" }}
            />
            <button
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="shrink-0 w-8 h-8 rounded-xl bg-amber-500 text-white flex items-center justify-center hover:bg-amber-600 disabled:opacity-40 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

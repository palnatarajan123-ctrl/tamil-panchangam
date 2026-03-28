// client/src/hooks/useChat.ts
import { useState, useCallback, useEffect } from "react";
import { authHeaders } from "@/lib/auth";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface ChatUsage {
  used: number;
  limit: number | null;
  unlimited: boolean;
  remaining: number | null;
}

export function useChat(baseChartId: string | undefined) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<ChatUsage | null>(null);

  // Load usage on mount
  useEffect(() => {
    if (!baseChartId) return;
    fetch(`/api/chat/usage/${baseChartId}`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setUsage(data))
      .catch(() => {});
  }, [baseChartId]);

  // Load history on mount
  useEffect(() => {
    if (!baseChartId) return;
    fetch(`/api/chat/history/${baseChartId}?limit=30`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        if (data.messages?.length) {
          setMessages(data.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
          })));
        }
      })
      .catch(() => {});
  }, [baseChartId]);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!baseChartId || isStreaming || !question.trim()) return;

      const userMsg: ChatMessage = { role: "user", content: question };
      setMessages((prev) => [...prev, userMsg]);
      setError(null);
      setIsStreaming(true);

      // Add placeholder assistant message
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", streaming: true },
      ]);

      try {
        const res = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            base_chart_id: baseChartId,
            question,
            history: messages.slice(-12).map((m) => ({
              role: m.role,
              content: m.content,
            })),
          }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Chat failed");
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const json = JSON.parse(line.slice(6));
              if (json.text) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last.role === "assistant") {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + json.text,
                      streaming: true,
                    };
                  }
                  return updated;
                });
              }
              if (json.done) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last.role === "assistant") {
                    updated[updated.length - 1] = { ...last, streaming: false };
                  }
                  return updated;
                });
                // Refresh usage count
                fetch(`/api/chat/usage/${baseChartId}`, { headers: authHeaders() })
                  .then((r) => r.json())
                  .then((data) => setUsage(data))
                  .catch(() => {});
              }
              if (json.error) throw new Error(json.error);
            } catch {}
          }
        }
      } catch (e: any) {
        setError(e.message || "Something went wrong");
        setMessages((prev) => prev.filter((m) => !m.streaming));
      } finally {
        setIsStreaming(false);
      }
    },
    [baseChartId, isStreaming, messages]
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, isStreaming, error, usage, sendMessage, clearMessages };
}

export const API_BASE = "/api";

import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { authHeaders, refreshAccessToken, clearTokens } from "./auth";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many requests. Please wait a moment and try again.");
    }
    if (res.status === 403) {
      throw new Error("Verification failed. Please complete the CAPTCHA and try again.");
    }
    if (res.status === 413) {
      throw new Error("Request too large. Please reduce the size of your input.");
    }
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown,
): Promise<Response> {
  const fullUrl = url.startsWith("/api")
    ? url
    : `/api${url.startsWith("/") ? url : `/${url}`}`;

  const headers: Record<string, string> = {
    ...authHeaders(),
    ...(data ? { "Content-Type": "application/json" } : {}),
  };

  let res = await fetch(fullUrl, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  // Auto-refresh on 401
  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders: Record<string, string> = {
        Authorization: `Bearer ${newToken}`,
        ...(data ? { "Content-Type": "application/json" } : {}),
      };
      res = await fetch(fullUrl, {
        method,
        headers: retryHeaders,
        body: data ? JSON.stringify(data) : undefined,
        credentials: "include",
      });
    } else {
      clearTokens();
    }
  }

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";

/**
 * 🔒 GLOBAL QUERY NORMALIZATION LAYER
 * This guarantees consistent shapes across the app.
 */
export const getQueryFn = <T>({ on401 }: {
  on401: UnauthorizedBehavior;
}): QueryFunction<T> =>
  async ({ queryKey }) => {
    const url = queryKey.join("/") as string;

    const res = await fetch(url, {
      credentials: "include",
    });

    if (on401 === "returnNull" && res.status === 401) {
      return null as T;
    }

    await throwIfResNotOk(res);
    const json = await res.json();

    // ✅ FIX: Normalize base-chart list response
    if (url === "/api/base-chart/list") {
      if (Array.isArray(json)) return json as T;
      if (Array.isArray(json?.charts)) return json.charts as T;
      return [] as T;
    }

    return json as T;
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});

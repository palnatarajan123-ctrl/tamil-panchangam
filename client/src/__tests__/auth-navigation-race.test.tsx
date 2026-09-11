// client/src/__tests__/auth-navigation-race.test.tsx
//
// Regression test for the Task 1 login-bounce bug (2026-09-08 through
// 2026-09-11): login.tsx used to call navigate("/") imperatively, right
// after AuthContext's setUser(), in the same synchronous block. Wouter's
// navigate() triggers an unbatched dispatchEvent() (confirmed in wouter's
// own source, `node_modules/wouter/esm/use-browser-location.js` -- the
// maintainers' own TODO acknowledges it isn't wrapped in
// unstable_batchedUpdates), which could force a re-render of AuthRoute
// before React flushed the pending setUser() update. AuthRoute would see
// a stale `user = null`, its effect would fire, and it silently bounced
// back to /login -- even though the login call itself fully succeeded
// (both attempts returned valid, sequential JWTs; this was never a
// backend or network problem).
//
// This is deliberately NOT a mirror/reimplementation of the app's auth
// components -- it imports and exercises the REAL AuthProvider, the REAL
// GuestRoute/AuthRoute from App.tsx, and the REAL Login page, wired up
// with wouter's real Switch/Route. apiRequest is the only thing mocked,
// standing in for the network, with an artificial delay so any race
// window has every opportunity to manifest.
//
// HONEST LIMITATION, found while building this test (2026-09-11) -- read
// before trusting this file's "regression protection" claim at face
// value: the original bug was first reproduced in a throwaway diagnostic
// script that invoked the login+navigate sequence as a bare async
// function call, entirely outside React's synthetic event system (no
// dispatched DOM event, no <form> involved). That repro showed the bounce
// reliably. When the SAME reintroduced bug (a bare `navigate("/")` added
// back after `await login(...)`) was driven through this test's REAL
// `<form>` submit -- a real dispatched "submit" DOM event, the same path
// a real click takes -- through the REAL Login component, the bounce did
// NOT reproduce, with or without wrapping the dispatch in React's act().
// Likely explanation: React 18's automatic batching may bind updates
// scheduled from within its own synthetic-event-dispatched handler (and
// their subsequent async continuations) into a single flush more
// reliably than an update chain that never passed through React's event
// system at all -- meaning the throwaway repro's trigger mechanism may
// have manufactured a race that doesn't reliably occur via a real click,
// at least on this exact React/wouter/Node combination.
//
// This does NOT mean the underlying risk isn't real -- wouter's dispatch
// still isn't wrapped in unstable_batchedUpdates (confirmed in its own
// source, with the maintainers' own acknowledged TODO), so the hazard
// class is genuine and the effect-driven fix (no imperative navigate
// anywhere in an auth-mutating handler; GuestRoute/AuthRoute react to
// committed state instead) is still unambiguously the more correct
// pattern regardless. It DOES mean: do not treat a green run of this
// file alone as proof a reintroduced `navigate()` would be caught --
// this suite could not be made to fail against that exact reintroduction
// via realistic DOM-driven interaction, despite real effort. Treat it as
// verifying the fix's happy path and the already-authenticated-on-mount
// case, not as a tripwire for regressions. A real browser is still the
// authority here, not this file.

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { Switch, Route } from "wouter";

import { AuthProvider } from "@/contexts/AuthContext";
import { AuthRoute, GuestRoute } from "@/App";
import Login from "@/pages/login";
import { apiRequest } from "@/lib/queryClient";

vi.mock("@/lib/queryClient", () => ({
  apiRequest: vi.fn(),
}));

const mockedApiRequest = vi.mocked(apiRequest);

function loginResponse() {
  return {
    json: async () => ({
      access_token: "fake-access-token",
      refresh_token: "fake-refresh-token",
      user: { id: "u1", email: "a@test.com", name: "A", role: "user" },
    }),
  } as Response;
}

function meResponse() {
  return {
    json: async () => ({
      user: { id: "u1", email: "a@test.com", name: "A", role: "user" },
    }),
  } as Response;
}

function HomeStub() {
  return <div data-testid="home-marker">HOME</div>;
}

function TestApp() {
  return (
    <AuthProvider>
      <Switch>
        <Route path="/login">
          <GuestRoute>
            <Login />
          </GuestRoute>
        </Route>
        <Route path="/">
          <AuthRoute>
            <HomeStub />
          </AuthRoute>
        </Route>
      </Switch>
    </AuthProvider>
  );
}

/**
 * Records every pathname the app navigates to, via the SAME events
 * wouter itself dispatches after monkey-patching history.pushState/
 * replaceState (see node_modules/wouter/esm/use-browser-location.js).
 *
 * This is the instrumentation that actually caught the original bug --
 * checking only the FINAL settled DOM/pathname state is not enough: with
 * GuestRoute now also watching `user` and navigating "/" -> home, a
 * reintroduced imperative navigate() in login.tsx can cause a transient
 * bounce to /login that GuestRoute then silently self-corrects a moment
 * later. The final state would look identical to a clean run, but a real
 * user would still see the page flash back to the login form. Tracking
 * the full sequence catches that regression even when it self-heals.
 */
function trackPathnameHistory(): { history: string[]; stop: () => void } {
  const history: string[] = [location.pathname];
  const record = () => history.push(location.pathname);
  window.addEventListener("pushState", record);
  window.addEventListener("replaceState", record);
  window.addEventListener("popstate", record);
  return {
    history,
    stop: () => {
      window.removeEventListener("pushState", record);
      window.removeEventListener("replaceState", record);
      window.removeEventListener("popstate", record);
    },
  };
}

describe("login navigation race (Task 1)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/login");
    container = document.createElement("div");
    document.body.appendChild(container);
    mockedApiRequest.mockReset();
  });

  it("lands on home after a single successful login, with no bounce back to /login", async () => {
    mockedApiRequest.mockImplementation(async () => {
      // Artificial network delay -- gives a real race window every
      // chance to manifest, same as the original headless repro.
      await new Promise((resolve) => setTimeout(resolve, 5));
      return loginResponse();
    });

    await act(async () => {
      root = createRoot(container);
      root.render(<TestApp />);
    });

    // Let the initial isLoading-resolution effect settle, same as a real
    // fresh page load.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(container.querySelector("#email")).toBeTruthy();

    const emailInput = container.querySelector("#email") as HTMLInputElement;
    const passwordInput = container.querySelector("#password") as HTMLInputElement;
    const form = container.querySelector("form") as HTMLFormElement;

    await act(async () => {
      emailInput.value = "a@test.com";
      emailInput.dispatchEvent(new Event("input", { bubbles: true }));
      passwordInput.value = "correct-password";
      passwordInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    const tracker = trackPathnameHistory();
    // Deliberately NOT wrapped in act() -- act() flushes React's pending
    // updates/effects at points that don't naturally occur in a real,
    // unmanaged browser event loop, which can mask exactly the kind of
    // out-of-band, unbatched-dispatchEvent race this test exists to
    // catch. Dispatching the real DOM event and waiting with a plain
    // timer mirrors how this bug was originally reproduced.
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await new Promise((r) => setTimeout(r, 50));
    tracker.stop();

    // The full navigation sequence must never revisit /login once the
    // submit fired -- not even transiently. A bare final-state check
    // can't tell a clean single navigation apart from a bounce-then-
    // self-correct, and the latter is still the bug from a real user's
    // point of view (a visible flash back to the login form).
    expect(tracker.history.slice(1)).not.toContain("/login");
    expect(window.location.pathname).toBe("/");
    expect(container.querySelector('[data-testid="home-marker"]')).toBeTruthy();
    expect(container.querySelector("#email")).toBeFalsy(); // login form is gone, not just hidden
  });

  it("does not loop or double-navigate when already authenticated on mount", async () => {
    localStorage.setItem("tp_access_token", "fake-access-token");
    localStorage.setItem("tp_refresh_token", "fake-refresh-token");
    // AuthProvider's mount effect calls GET /api/auth/me when a token is
    // already present in localStorage -- this is that call, not a login.
    mockedApiRequest.mockImplementation(async () => meResponse());

    await act(async () => {
      root = createRoot(container);
      root.render(<TestApp />);
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(window.location.pathname).toBe("/");
    expect(container.querySelector('[data-testid="home-marker"]')).toBeTruthy();
  });
});

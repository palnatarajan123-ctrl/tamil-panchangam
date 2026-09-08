import { Switch, Route, useLocation } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Navigation } from "@/components/navigation";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { useEffect, type ReactNode } from "react";

import Home from "@/pages/home";
import Predictions from "@/pages/predictions.legacy"; // legacy
import Health from "@/pages/health";
import Docs from "@/pages/docs";
import ChartDetail from "@/pages/chart-detail";
import ProspectDetail from "@/pages/prospect-detail";
import AdminLLM from "@/pages/admin-llm";
import MethodologyPage from "@/pages/methodology";
import Login from "@/pages/login";
import Register from "@/pages/register";
import MyCharts from "@/pages/my-charts";
import AdminDashboard from "@/pages/admin/index";
import NotFound from "@/pages/not-found";

import PredictionScreen from "@/screens/prediction-screen";
import FamilyScreen from "@/screens/family-screen";
import FamilyPredictionScreen from "@/screens/family-prediction-screen";
import FamilyTimelineScreen from "@/screens/family-timeline-screen";
import ChildrenTimingScreen from "@/screens/children-timing-screen";
import ChildPredictionScreen from "@/screens/child-prediction-screen";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";


/* -------------------------------------------------
   ADMIN ROUTE GUARD
-------------------------------------------------- */

function AdminRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const [, navigate] = useLocation();

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "admin")) {
      navigate("/");
    }
  }, [user, isLoading, navigate]);

  if (isLoading) return null;
  if (!user || user.role !== "admin") return null;
  return <>{children}</>;
}

/* -------------------------------------------------
   AUTH ROUTE GUARD (security fix, 2026-09-08)

   Chart creation and every prediction-related screen now require a
   logged-in user, matching the backend's Phase 2 auth requirement on the
   endpoints these screens call. Unlike AdminRoute (which silently renders
   nothing and lets the user sit on a blank page), this redirects to
   /login so a logged-out visitor has a clear path forward instead of a
   dead end.
-------------------------------------------------- */

function AuthRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const [, navigate] = useLocation();

  useEffect(() => {
    if (!isLoading && !user) {
      navigate("/login");
    }
  }, [user, isLoading, navigate]);

  if (isLoading) return null;
  if (!user) return null;
  return <>{children}</>;
}

/* -------------------------------------------------
   ROUTER (ALL ROUTES LIVE HERE)
-------------------------------------------------- */

function Router() {
  return (
    <Switch>
      {/* ---------------------------------
         Predictions Routes (auth required, security fix 2026-09-08)
         --------------------------------- */}
      <Route path="/predictions/:id">
        <AuthRoute><Predictions /></AuthRoute>
      </Route>
      <Route path="/predictions">
        <AuthRoute>
          <div className="container max-w-2xl mx-auto py-12">
            <Card>
              <CardContent className="py-10 text-center space-y-4">
                <div className="text-muted-foreground">
                  Please open a specific birth chart first, then generate predictions.
                </div>
                <Link href="/">
                  <Button variant="outline">Go to Birth Charts</Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </AuthRoute>
      </Route>

      {/* Static pages (correctly public) */}
      <Route path="/health" component={Health} />
      <Route path="/docs" component={Docs} />
      <Route path="/methodology" component={MethodologyPage} />
      <Route path="/admin/llm">
        <AdminRoute><AdminLLM /></AdminRoute>
      </Route>

      {/* Auth pages (correctly public) */}
      <Route path="/login" component={Login} />
      <Route path="/register" component={Register} />

      {/* Auth required (security fix, 2026-09-08) */}
      <Route path="/my-charts">
        <AuthRoute><MyCharts /></AuthRoute>
      </Route>
      <Route path="/family/:groupId/members/:memberId/predictions">
        <AuthRoute><ChildPredictionScreen /></AuthRoute>
      </Route>
      <Route path="/family/:groupId/children-timing">
        <AuthRoute><ChildrenTimingScreen /></AuthRoute>
      </Route>
      <Route path="/family/:groupId/timeline">
        <AuthRoute><FamilyTimelineScreen /></AuthRoute>
      </Route>
      <Route path="/family/:groupId/predictions">
        <AuthRoute><FamilyPredictionScreen /></AuthRoute>
      </Route>
      <Route path="/family">
        <AuthRoute><FamilyScreen /></AuthRoute>
      </Route>

      {/* Admin dashboard */}
      <Route path="/admin">
        <AdminRoute><AdminDashboard /></AdminRoute>
      </Route>

      {/* ---------------------------------
         Birth Chart (STRUCTURE) -- auth required, security fix 2026-09-08
         --------------------------------- */}
      <Route path="/chart/:id">
        <AuthRoute><ChartDetail /></AuthRoute>
      </Route>

      {/* ---------------------------------
         EPIC-6 Predictions (DERIVED) -- auth required, security fix 2026-09-08
         --------------------------------- */}
      <Route path="/chart/:id/predictions">
        <AuthRoute><PredictionScreen /></AuthRoute>
      </Route>

      {/* ---------------------------------
         Phase G1-G4: chart-to-chart prospect Porutham detail view
         -- auth required, security fix 2026-09-08
         --------------------------------- */}
      <Route path="/chart/:chartId/prospects/:prospectId">
        <AuthRoute><ProspectDetail /></AuthRoute>
      </Route>

      {/* ---------------------------------
         Home (MUST BE LAST) -- auth required, security fix 2026-09-08
         (chart creation flow lives here)
         --------------------------------- */}
      <Route path="/">
        <AuthRoute><Home /></AuthRoute>
      </Route>

      {/* Fallback */}
      <Route component={NotFound} />
    </Switch>
  );
}

/* -------------------------------------------------
   APP ROOT (PROVIDERS + NAV)
-------------------------------------------------- */

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <div className="min-h-screen bg-background">
            <Navigation />
            <main className="container mx-auto p-4">
              <Router />
            </main>
          </div>
          <Toaster />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

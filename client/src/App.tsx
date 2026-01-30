import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Navigation } from "@/components/navigation";

import Home from "@/pages/home";
import Predictions from "@/pages/predictions"; // legacy
import Health from "@/pages/health";
import Docs from "@/pages/docs";
import ChartDetail from "@/pages/chart-detail";
import AdminLLM from "@/pages/admin-llm";
import NotFound from "@/pages/not-found";

import PredictionScreen from "@/screens/prediction-screen";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";


/* -------------------------------------------------
   ROUTER (ALL ROUTES LIVE HERE)
-------------------------------------------------- */

function Router() {
  return (
    <Switch>
      {/* ---------------------------------
         Predictions Routes
         --------------------------------- */}
      <Route path="/predictions/:id" component={Predictions} />
      <Route path="/predictions">
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
      </Route>

      {/* Static pages */}
      <Route path="/health" component={Health} />
      <Route path="/docs" component={Docs} />
      <Route path="/admin/llm" component={AdminLLM} />

      {/* ---------------------------------
         Birth Chart (STRUCTURE)
         --------------------------------- */}
      <Route path="/chart/:id" component={ChartDetail} />

      {/* ---------------------------------
         EPIC-6 Predictions (DERIVED)
         --------------------------------- */}
      <Route
        path="/chart/:id/predictions"
        component={PredictionScreen}
      />

      {/* ---------------------------------
         Home (MUST BE LAST)
         --------------------------------- */}
      <Route path="/" component={Home} />

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
      <TooltipProvider>
        <div className="min-h-screen bg-background">
          <Navigation />
          <main className="container mx-auto p-4">
            <Router />
          </main>
        </div>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

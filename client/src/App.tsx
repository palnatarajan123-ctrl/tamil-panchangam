import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Navigation } from "@/components/navigation";
import Home from "@/pages/home";
import Predictions from "@/pages/predictions";
import Health from "@/pages/health";
import Reports from "@/pages/reports";
import Docs from "@/pages/docs";
import ChartDetail from "@/pages/chart-detail";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/predictions" component={Predictions} />
      <Route path="/reports" component={Reports} />
      <Route path="/health" component={Health} />
      <Route path="/docs" component={Docs} />
      <Route path="/chart/:id" component={ChartDetail} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <div className="min-h-screen bg-background">
          <Navigation />
          <main>
            <Router />
          </main>
        </div>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

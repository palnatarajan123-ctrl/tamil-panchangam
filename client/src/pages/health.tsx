import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Activity, Server, Calculator, Globe } from "lucide-react";
import type { HealthStatus } from "@shared/schema";

export default function Health() {
  const { data: health, isLoading, error } = useQuery<HealthStatus>({
    queryKey: ["/api/health"],
    refetchInterval: 30000,
  });

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
          <Activity className="h-8 w-8 text-primary" />
          System Health
        </h1>
        <p className="text-muted-foreground">
          Monitor the status of the Tamil Panchangam Engine services.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              API Status
            </CardTitle>
            <CardDescription>Core engine availability</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-32" />
            ) : error ? (
              <StatusBadge status="error" label="Unavailable" />
            ) : (
              <StatusBadge 
                status={health?.status === "ok" ? "ok" : "error"} 
                label={health?.status === "ok" ? "Operational" : "Issue Detected"}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Calculation Method
            </CardTitle>
            <CardDescription>Astronomical calculation engine</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-32" />
            ) : (
              <div className="space-y-2">
                <div className="text-lg font-semibold">
                  {health?.calculation_method || "Drik Ganita"}
                </div>
                <p className="text-sm text-muted-foreground">
                  Modern astronomical calculations
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Ayanamsa
            </CardTitle>
            <CardDescription>Sidereal zodiac reference</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-32" />
            ) : (
              <div className="space-y-2">
                <div className="text-lg font-semibold">
                  {health?.ayanamsa || "Lahiri"}
                </div>
                <p className="text-sm text-muted-foreground">
                  Official Indian Ephemeris standard
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Service Info
            </CardTitle>
            <CardDescription>Engine identification</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-48" />
            ) : (
              <div className="space-y-2">
                <div className="text-lg font-semibold">
                  {health?.service || "Tamil Panchangam Engine"}
                </div>
                <p className="text-sm text-muted-foreground font-mono">
                  v0.1.0
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Services Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span>Base Chart Service</span>
              </div>
              <span className="text-sm text-muted-foreground">Immutable birth chart computation</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span>Prediction Service</span>
              </div>
              <span className="text-sm text-muted-foreground">Temporal transit analysis</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Ephemeris Engine</span>
              </div>
              <span className="text-sm text-muted-foreground">Swiss Ephemeris (stub)</span>
            </div>
            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-500" />
                <span>PDF Report Builder</span>
              </div>
              <span className="text-sm text-muted-foreground">ReportLab (stub)</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

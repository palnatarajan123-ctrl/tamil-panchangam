import { useParams, Link } from "wouter";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import { PredictionTimeline } from "@/components/prediction/PredictionTimeline";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

import {
  Calendar,
  Loader2,
  Sparkles,
  ArrowLeft,
} from "lucide-react";

/* -----------------------------------------------------
   Constants
----------------------------------------------------- */

const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December"
];

/* -----------------------------------------------------
   Validation
----------------------------------------------------- */

const schema = z.object({
  year: z.string().refine(v => !isNaN(+v) && +v >= 1900 && +v <= 2100),
  month: z.string().refine(v => !isNaN(+v) && +v >= 1 && +v <= 12),
});

type FormValues = z.infer<typeof schema>;

/* -----------------------------------------------------
   Types
----------------------------------------------------- */

interface BaseChartResponse {
  id: string;
  locked: boolean;
  data: {
    birth_details: {
      name?: string;
      date_of_birth: string;
      time_of_birth: string;
      place_of_birth: string;
      latitude: number;
      longitude: number;
      timezone: string;
    };
  };
}

/* -----------------------------------------------------
   Prediction Request Builder (EPIC-10)
----------------------------------------------------- */

function buildPredictionRequest(
  baseChartId: string,
  year: number,
  month: number
) {
  return {
    base_chart_id: baseChartId,
    timeframe: { mode: "monthly", year, month },
    triggers: { transits: true, dasha: true, nakshatra: true },
    levers: {
      houses: true,
      planets: true,
      nakshatras: true,
      aspects: false,
    },
    focus_areas: [
      "career",
      "finance",
      "relationships",
      "health",
      "personal_growth",
    ],
    constraints: {
      tone: "balanced",
      confidence_threshold: 0.6,
    },
    output: {
      detail_level: "standard",
      include_timing: true,
      include_remedies: false,
      format: "ui",
    },
  };
}

/* -----------------------------------------------------
   Page
----------------------------------------------------- */

export default function Predictions() {
  const { id: baseChartId } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [prediction, setPrediction] = useState<any | null>(null);
  const predictionData = prediction?.data ?? null;


  const now = new Date();
  const timelineMonths = Array.from({ length: 6 }).map((_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - 2 + i, 1);
    return {
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      available: predictionData
      ? predictionData.available_periods?.some(
          (p: any) =>
            p.year === d.getFullYear() &&
            p.month === d.getMonth() + 1
        )
      : false,

    };
  });

  const { data: chart, isLoading, error } = useQuery<BaseChartResponse>({
    queryKey: ["/api/base-chart", baseChartId],
    enabled: !!baseChartId,
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/base-chart/${baseChartId}`);
      if (!res.ok) throw new Error("Birth chart not found");
      return res.json();
    },
  });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      year: new Date().getFullYear().toString(),
      month: (new Date().getMonth() + 1).toString(),
    },
  });

  const handleTimelineSelect = (year: number, month: number) => {
    form.setValue("year", year.toString());
    form.setValue("month", month.toString());
  };

  const mutation = useMutation({
    mutationFn: async (v: FormValues) => {
      const payload = buildPredictionRequest(
        baseChartId!,
        Number(v.year),
        Number(v.month)
      );
      const res = await apiRequest("POST", "/api/prediction/request", payload);
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: data => {
      setPrediction(data);
      toast({ title: "Prediction Generated", description: "Monthly prediction ready" });
    },
    onError: (e: Error) => {
      toast({ title: "Prediction failed", description: e.message, variant: "destructive" });
    },
  });

  if (isLoading) {
    return (
      <div className="container max-w-6xl mx-auto px-4 py-12">
        <Skeleton className="h-8 w-64 mb-6" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !chart) {
    return (
      <div className="container max-w-4xl mx-auto px-4 py-12">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">Birth chart not found</p>
            <Link href="/">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const name = chart.data.birth_details.name || "Birth Chart";

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-4">
        <Link href={`/chart/${baseChartId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
            <Sparkles className="h-8 w-8 text-primary" />
            Monthly Predictions
          </h1>
          <p className="text-muted-foreground">
            Explicit intent · deterministic engine
          </p>
        </div>
        <StatusBadge status="ok" />
      </div>

      <PredictionTimeline
        months={timelineMonths}
        selectedYear={Number(form.watch("year"))}
        selectedMonth={Number(form.watch("month"))}
        onSelect={handleTimelineSelect}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-6">
        {/* FORM */}
        <Card>
          <CardHeader>
            <CardTitle>{name}</CardTitle>
            <CardDescription>
              Immutable chart → explicit prediction request
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(v => mutation.mutate(v))}
                className="space-y-6"
              >
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="year"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Year</FormLabel>
                        <FormControl>
                          <Input type="number" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="month"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Month</FormLabel>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {MONTHS.map((m, i) => (
                              <SelectItem key={i} value={(i + 1).toString()}>
                                {m}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <Button type="submit" className="w-full" disabled={mutation.isPending}>
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Calendar className="mr-2 h-4 w-4" />
                      Generate Prediction
                    </>
                  )}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        {/* RESULT */}
        <Card>
          <CardHeader>
            <CardTitle>Prediction Result</CardTitle>
            <CardDescription>UI-ready prediction snapshot</CardDescription>
          </CardHeader>
          <CardContent>
            {predictionData ? (
              <div className="space-y-6">
                <MonthlyPredictionView prediction={predictionData} />

                {predictionData.explainability && (
                  <ExplainabilityDrawer
                    explainability={predictionData.explainability}
                  />
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground">
                <Calendar className="h-12 w-12 mx-auto mb-4 opacity-20" />
                Generate a prediction to see results
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

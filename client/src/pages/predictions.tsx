import { useParams, Link } from "wouter";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { MonthlyPredictionView } from "@/components/prediction/MonthlyPredictionView";
import { ExplainabilityDrawer } from "@/components/prediction/ExplainabilityDrawer";
import { adaptMonthlyPrediction } from "@/adapters/predictionAdapter";

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
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/* -----------------------------------------------------
   Validation (dynamic per type)
----------------------------------------------------- */

const monthlySchema = z.object({
  year: z.string(),
  month: z.string(),
});

const weeklySchema = z.object({
  year: z.string(),
  week: z.string(),
});

const yearlySchema = z.object({
  year: z.string(),
});

/* -----------------------------------------------------
   Page
----------------------------------------------------- */

export default function Predictions() {
  const { id } = useParams<{ id: string }>();
  const baseChartId = id;

  const { toast } = useToast();

  const [prediction, setPrediction] = useState<any | null>(null);
  const [predictionType, setPredictionType] = useState<
    "monthly" | "weekly" | "yearly"
  >("monthly");

  /* ---------------- Guard ---------------- */

  if (!baseChartId) {
    return (
      <div className="container max-w-4xl mx-auto px-4 py-12 text-muted-foreground">
        Select a birth chart
      </div>
    );
  }

  /* ---------------- Fetch Birth Chart ---------------- */

  const { data: chart, isLoading, error } = useQuery({
    queryKey: ["/api/base-chart", baseChartId],
    queryFn: async () => {
      const res = await fetch(`/api/base-chart/${baseChartId}`);
      if (!res.ok) throw new Error("Birth chart not found");
      return res.json();
    },
  });

  /* ---------------- Form ---------------- */

  const form = useForm<any>({
    resolver: zodResolver(
      predictionType === "monthly"
        ? monthlySchema
        : predictionType === "weekly"
        ? weeklySchema
        : yearlySchema
    ),
    defaultValues: {
      year: new Date().getFullYear().toString(),
      month: (new Date().getMonth() + 1).toString(),
      week: "1",
    },
  });

  /* ---------------- Mutation ---------------- */

  const mutation = useMutation({
    mutationFn: async (v: any) => {
      const basePayload = {
        base_chart_id: baseChartId,
        year: Number(v.year),
      };

      let endpoint = "/api/prediction/monthly";
      let payload: any = basePayload;

      if (predictionType === "monthly") {
        payload.month = Number(v.month);
      } else if (predictionType === "weekly") {
        endpoint = "/api/prediction/weekly";
        payload.week = Number(v.week);
      } else {
        endpoint = "/api/prediction/yearly";
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      return res.json();
    },

    onSuccess: data => {
      setPrediction(adaptMonthlyPrediction(data.details));
      toast({
        title: "Prediction Generated",
        description: `${predictionType} prediction ready`,
      });
    },

    onError: (e: Error) => {
      toast({
        title: "Prediction failed",
        description: e.message,
        variant: "destructive",
      });
    },
  });

  /* ---------------- Loading ---------------- */

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
        Birth chart not found
      </div>
    );
  }

  /* ---------------- UI ---------------- */

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">

      {/* HEADER */}
      <div className="flex items-center gap-4 mb-6">
        <Link href={`/chart/${baseChartId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft />
          </Button>
        </Link>

        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Sparkles /> Predictions
        </h1>

        <StatusBadge status="ok" />
      </div>

      {/* TABS */}
      <div className="flex gap-2 mb-6">
        {["monthly", "weekly", "yearly"].map(t => (
          <Button
            key={t}
            variant={predictionType === t ? "default" : "outline"}
            onClick={() => {
              setPredictionType(t as any);
              setPrediction(null);
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </Button>
        ))}
      </div>

      {/* FORM */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(v => mutation.mutate(v))}
              className="grid grid-cols-1 md:grid-cols-3 gap-4"
            >
              <FormField
                control={form.control}
                name="year"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Year</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {predictionType === "monthly" && (
                <FormField
                  control={form.control}
                  name="month"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Month</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger />
                        </FormControl>
                        <SelectContent>
                          {MONTHS.map((m, i) => (
                            <SelectItem key={i} value={(i + 1).toString()}>
                              {m}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
              )}

              {predictionType === "weekly" && (
                <FormField
                  control={form.control}
                  name="week"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>ISO Week</FormLabel>
                      <FormControl>
                        <Input type="number" {...field} />
                      </FormControl>
                    </FormItem>
                  )}
                />
              )}

              <Button
                type="submit"
                className="md:col-span-3"
                disabled={mutation.isPending}
              >
                {mutation.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    <Calendar className="mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* RESULT */}
      {prediction && (
        <MonthlyPredictionView prediction={prediction} />
      )}

      {prediction?.disclaimers && (
        <ExplainabilityDrawer explainability={prediction} />
      )}
    </div>
  );
}

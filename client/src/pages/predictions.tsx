import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { Calendar, Loader2, Sparkles } from "lucide-react";
import type { BaseChart, MonthlyPrediction } from "@shared/schema";

const predictionSchema = z.object({
  chartId: z.string().min(1, "Select a chart"),
  year: z.string().refine((val) => !isNaN(parseInt(val)) && parseInt(val) >= 1900 && parseInt(val) <= 2100, "Valid year required"),
  month: z.string().refine((val) => !isNaN(parseInt(val)) && parseInt(val) >= 1 && parseInt(val) <= 12, "Valid month required"),
});

type PredictionFormValues = z.infer<typeof predictionSchema>;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

export default function Predictions() {
  const { toast } = useToast();
  const [prediction, setPrediction] = useState<MonthlyPrediction | null>(null);

  const { data: charts, isLoading: chartsLoading } = useQuery<BaseChart[]>({
    queryKey: ["/api/base-chart/list"],
  });

  const form = useForm<PredictionFormValues>({
    resolver: zodResolver(predictionSchema),
    defaultValues: {
      chartId: "",
      year: new Date().getFullYear().toString(),
      month: (new Date().getMonth() + 1).toString(),
    },
  });

  const generateMutation = useMutation({
    mutationFn: async (values: PredictionFormValues) => {
      const payload = {
        base_chart_id: values.chartId,
        year: parseInt(values.year),
        months: [parseInt(values.month)],
      };
      const response = await apiRequest("POST", "/api/prediction/monthly", payload);
      return response.json();
    },
    onSuccess: (data) => {
      setPrediction(data);
      toast({
        title: "Prediction Generated",
        description: `Monthly prediction for ${MONTHS[parseInt(form.getValues("month")) - 1]} ${form.getValues("year")} created.`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to generate prediction",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (values: PredictionFormValues) => {
    generateMutation.mutate(values);
  };

  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
          <Calendar className="h-8 w-8 text-primary" />
          Monthly Predictions
        </h1>
        <p className="text-muted-foreground">
          Generate transit-based predictions for any month using stored birth chart data.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Generate Prediction
            </CardTitle>
            <CardDescription>
              Select a birth chart and target month for prediction analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                  control={form.control}
                  name="chartId"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Birth Chart</FormLabel>
                      {chartsLoading ? (
                        <Skeleton className="h-10 w-full" />
                      ) : (
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="select-chart">
                              <SelectValue placeholder="Select a birth chart" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {charts?.map((chart) => (
                              <SelectItem key={chart.id} value={chart.id}>
                                {chart.name} - {chart.date_of_birth}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="year"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Year</FormLabel>
                        <FormControl>
                          <Input 
                            type="number" 
                            {...field} 
                            data-testid="input-prediction-year"
                          />
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
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger data-testid="select-month">
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {MONTHS.map((month, index) => (
                              <SelectItem key={index} value={(index + 1).toString()}>
                                {month}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={generateMutation.isPending || !charts?.length}
                  data-testid="button-generate-prediction"
                >
                  {generateMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
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

        <Card>
          <CardHeader>
            <CardTitle>Prediction Result</CardTitle>
            <CardDescription>
              Transit analysis and monthly forecast
            </CardDescription>
          </CardHeader>
          <CardContent>
            {prediction ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Status</span>
                  <StatusBadge status={prediction.status === "stub" ? "stub" : "ok"} />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">Chart ID</span>
                    <span className="font-mono">{prediction.base_chart_id.substring(0, 12)}...</span>
                  </div>
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">Period</span>
                    <span>{MONTHS[prediction.months[0] - 1]} {prediction.year}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">Generated</span>
                    <span className="font-mono text-xs">{new Date(prediction.generated_at).toLocaleString()}</span>
                  </div>
                </div>
                <div className="p-4 bg-muted/50 rounded-md">
                  <p className="text-sm text-muted-foreground">{prediction.message}</p>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground">
                <Calendar className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>Generate a prediction to see results here</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

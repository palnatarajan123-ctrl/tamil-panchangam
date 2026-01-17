import { useForm } from "react-hook-form";
import { useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";

import { Loader2, Sparkles, MapPin, Clock, User } from "lucide-react";

/* -----------------------------------------------------
   Helpers
----------------------------------------------------- */

async function geocodeCity(city: string) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
    city
  )}`;

  const res = await fetch(url, {
    headers: {
      "User-Agent": "tamil-panchangam-engine",
    },
  });

  const data = await res.json();

  if (!data || data.length === 0) {
    throw new Error("Location not found");
  }

  return {
    latitude: parseFloat(data[0].lat),
    longitude: parseFloat(data[0].lon),
  };
}

/* -----------------------------------------------------
   Schema
----------------------------------------------------- */

const formSchema = z.object({
  name: z.string().min(1, "Name is required"),
  sex: z.enum(["M", "F", "O"]).optional(),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  timeOfBirth: z.string().min(1, "Time of birth is required"),
  placeOfBirth: z.string().min(1, "Place of birth is required"),
  latitude: z.string(),
  longitude: z.string(),
  timezone: z.string().min(1, "Timezone is required"),
});

type FormValues = z.infer<typeof formSchema>;

interface ChartFormProps {
  onSuccess?: (chartId: string) => void;
}

/* -----------------------------------------------------
   Component
----------------------------------------------------- */

export function ChartForm({ onSuccess }: ChartFormProps) {
  const { toast } = useToast();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      sex: undefined,
      dateOfBirth: "",
      timeOfBirth: "",
      placeOfBirth: "",
      latitude: "",
      longitude: "",
      timezone: "Asia/Kolkata",
    },
  });

  const handlePlaceBlur = async (place: string) => {
    if (!place || place.trim().length < 3) return;

    try {
      const { latitude, longitude } = await geocodeCity(place);
      form.setValue("latitude", latitude.toString(), { shouldValidate: true });
      form.setValue("longitude", longitude.toString(), { shouldValidate: true });
    } catch {
      toast({
        title: "Location not found",
        description: "Please enter latitude and longitude manually.",
        variant: "destructive",
      });
    }
  };

  /* -----------------------------------------------------
     Mutation
  ----------------------------------------------------- */

  const createChartMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        name: values.name,
        sex: values.sex,
        date_of_birth: values.dateOfBirth,
        time_of_birth: values.timeOfBirth,
        place_of_birth: values.placeOfBirth,
        latitude: parseFloat(values.latitude),
        longitude: parseFloat(values.longitude),
        timezone: values.timezone,
      };

      const res = await apiRequest(
        "POST",
        "/api/base-chart/create",
        payload
      );

      const data = await res.json();

      if (!data?.base_chart_id) {
        throw new Error("Base chart ID missing from response");
      }

      return data;
    },

    onSuccess: (data) => {
      toast({
        title: "Chart Created",
        description: "Birth chart generated successfully.",
      });

      queryClient.invalidateQueries({
        queryKey: ["/api/base-chart/list"],
      });

      onSuccess?.(data.base_chart_id);

      form.reset();
    },

    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to create chart",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (values: FormValues) => {
    createChartMutation.mutate(values);
  };

  /* -----------------------------------------------------
     UI
  ----------------------------------------------------- */

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-serif flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          Birth Chart Details
        </CardTitle>
        <CardDescription>
          Enter birth details for accurate Panchangam calculations (Drik Ganita)
        </CardDescription>
      </CardHeader>

      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Personal */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <User className="h-4 w-4" />
                Personal Details
              </div>

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Full Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter full name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="sex"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sex</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full border rounded px-3 py-2 bg-background"
                      >
                        <option value="">Select</option>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                        <option value="O">Other</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Date / Time */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Clock className="h-4 w-4" />
                Date & Time
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="dateOfBirth"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Date of Birth</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="timeOfBirth"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Time of Birth</FormLabel>
                      <FormControl>
                        <Input type="time" step="1" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Location */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <MapPin className="h-4 w-4" />
                Location
              </div>

              <FormField
                control={form.control}
                name="placeOfBirth"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Place of Birth</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="City, Country"
                        {...field}
                        onBlur={(e) => {
                          field.onBlur();
                          handlePlaceBlur(e.target.value);
                        }}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <FormField
                  control={form.control}
                  name="latitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Latitude</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.0001" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="longitude"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Longitude</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.0001" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="timezone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Timezone</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={createChartMutation.isPending}
            >
              {createChartMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating Chart...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Birth Chart
                </>
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

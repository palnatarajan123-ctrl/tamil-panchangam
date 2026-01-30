import { useForm } from "react-hook-form";
import { useState, useMemo } from "react";

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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";

import { Loader2, Sparkles, MapPin, Clock, User, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

/* -----------------------------------------------------
   City Data (Embedded LOV)
----------------------------------------------------- */

interface CityEntry {
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

const CITIES_LOV: CityEntry[] = [
  {"city": "Chennai", "country": "India", "latitude": 13.0827, "longitude": 80.2707, "timezone": "Asia/Kolkata"},
  {"city": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
  {"city": "Delhi", "country": "India", "latitude": 28.7041, "longitude": 77.1025, "timezone": "Asia/Kolkata"},
  {"city": "Bangalore", "country": "India", "latitude": 12.9716, "longitude": 77.5946, "timezone": "Asia/Kolkata"},
  {"city": "Kolkata", "country": "India", "latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"},
  {"city": "Hyderabad", "country": "India", "latitude": 17.3850, "longitude": 78.4867, "timezone": "Asia/Kolkata"},
  {"city": "Pune", "country": "India", "latitude": 18.5204, "longitude": 73.8567, "timezone": "Asia/Kolkata"},
  {"city": "Ahmedabad", "country": "India", "latitude": 23.0225, "longitude": 72.5714, "timezone": "Asia/Kolkata"},
  {"city": "Jaipur", "country": "India", "latitude": 26.9124, "longitude": 75.7873, "timezone": "Asia/Kolkata"},
  {"city": "Lucknow", "country": "India", "latitude": 26.8467, "longitude": 80.9462, "timezone": "Asia/Kolkata"},
  {"city": "Coimbatore", "country": "India", "latitude": 11.0168, "longitude": 76.9558, "timezone": "Asia/Kolkata"},
  {"city": "Madurai", "country": "India", "latitude": 9.9252, "longitude": 78.1198, "timezone": "Asia/Kolkata"},
  {"city": "Kochi", "country": "India", "latitude": 9.9312, "longitude": 76.2673, "timezone": "Asia/Kolkata"},
  {"city": "Thiruvananthapuram", "country": "India", "latitude": 8.5241, "longitude": 76.9366, "timezone": "Asia/Kolkata"},
  {"city": "Surat", "country": "India", "latitude": 21.1702, "longitude": 72.8311, "timezone": "Asia/Kolkata"},
  {"city": "Varanasi", "country": "India", "latitude": 25.3176, "longitude": 82.9739, "timezone": "Asia/Kolkata"},
  {"city": "Mysore", "country": "India", "latitude": 12.2958, "longitude": 76.6394, "timezone": "Asia/Kolkata"},
  {"city": "Chandigarh", "country": "India", "latitude": 30.7333, "longitude": 76.7794, "timezone": "Asia/Kolkata"},
  {"city": "Amritsar", "country": "India", "latitude": 31.6340, "longitude": 74.8723, "timezone": "Asia/Kolkata"},
  {"city": "Goa", "country": "India", "latitude": 15.2993, "longitude": 74.1240, "timezone": "Asia/Kolkata"},
  {"city": "Pondicherry", "country": "India", "latitude": 11.9416, "longitude": 79.8083, "timezone": "Asia/Kolkata"},
  {"city": "New York", "country": "USA", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
  {"city": "Los Angeles", "country": "USA", "latitude": 34.0522, "longitude": -118.2437, "timezone": "America/Los_Angeles"},
  {"city": "Chicago", "country": "USA", "latitude": 41.8781, "longitude": -87.6298, "timezone": "America/Chicago"},
  {"city": "San Francisco", "country": "USA", "latitude": 37.7749, "longitude": -122.4194, "timezone": "America/Los_Angeles"},
  {"city": "Seattle", "country": "USA", "latitude": 47.6062, "longitude": -122.3321, "timezone": "America/Los_Angeles"},
  {"city": "Boston", "country": "USA", "latitude": 42.3601, "longitude": -71.0589, "timezone": "America/New_York"},
  {"city": "Dallas", "country": "USA", "latitude": 32.7767, "longitude": -96.7970, "timezone": "America/Chicago"},
  {"city": "Austin", "country": "USA", "latitude": 30.2672, "longitude": -97.7431, "timezone": "America/Chicago"},
  {"city": "London", "country": "UK", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
  {"city": "Manchester", "country": "UK", "latitude": 53.4808, "longitude": -2.2426, "timezone": "Europe/London"},
  {"city": "Toronto", "country": "Canada", "latitude": 43.6532, "longitude": -79.3832, "timezone": "America/Toronto"},
  {"city": "Vancouver", "country": "Canada", "latitude": 49.2827, "longitude": -123.1207, "timezone": "America/Vancouver"},
  {"city": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"},
  {"city": "Melbourne", "country": "Australia", "latitude": -37.8136, "longitude": 144.9631, "timezone": "Australia/Melbourne"},
  {"city": "Singapore", "country": "Singapore", "latitude": 1.3521, "longitude": 103.8198, "timezone": "Asia/Singapore"},
  {"city": "Hong Kong", "country": "Hong Kong", "latitude": 22.3193, "longitude": 114.1694, "timezone": "Asia/Hong_Kong"},
  {"city": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
  {"city": "Dubai", "country": "UAE", "latitude": 25.2048, "longitude": 55.2708, "timezone": "Asia/Dubai"},
  {"city": "Kuala Lumpur", "country": "Malaysia", "latitude": 3.1390, "longitude": 101.6869, "timezone": "Asia/Kuala_Lumpur"},
  {"city": "Bangkok", "country": "Thailand", "latitude": 13.7563, "longitude": 100.5018, "timezone": "Asia/Bangkok"},
  {"city": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone": "Europe/Paris"},
  {"city": "Berlin", "country": "Germany", "latitude": 52.5200, "longitude": 13.4050, "timezone": "Europe/Berlin"},
  {"city": "Amsterdam", "country": "Netherlands", "latitude": 52.3676, "longitude": 4.9041, "timezone": "Europe/Amsterdam"},
  {"city": "Zurich", "country": "Switzerland", "latitude": 47.3769, "longitude": 8.5417, "timezone": "Europe/Zurich"},
  {"city": "Dublin", "country": "Ireland", "latitude": 53.3498, "longitude": -6.2603, "timezone": "Europe/Dublin"},
  {"city": "Colombo", "country": "Sri Lanka", "latitude": 6.9271, "longitude": 79.8612, "timezone": "Asia/Colombo"},
  {"city": "Dhaka", "country": "Bangladesh", "latitude": 23.8103, "longitude": 90.4125, "timezone": "Asia/Dhaka"},
  {"city": "Kathmandu", "country": "Nepal", "latitude": 27.7172, "longitude": 85.3240, "timezone": "Asia/Kathmandu"},
  {"city": "Karachi", "country": "Pakistan", "latitude": 24.8607, "longitude": 67.0011, "timezone": "Asia/Karachi"},
  {"city": "Lahore", "country": "Pakistan", "latitude": 31.5204, "longitude": 74.3587, "timezone": "Asia/Karachi"},
];

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
  const [cityOpen, setCityOpen] = useState(false);
  const [citySearch, setCitySearch] = useState("");
  const [isManualEntry, setIsManualEntry] = useState(false);

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

  const filteredCities = useMemo(() => {
    if (!citySearch) return CITIES_LOV.slice(0, 20);
    const lower = citySearch.toLowerCase();
    return CITIES_LOV.filter(
      (c) =>
        c.city.toLowerCase().includes(lower) ||
        c.country.toLowerCase().includes(lower)
    ).slice(0, 20);
  }, [citySearch]);

  const handleCitySelect = (city: CityEntry) => {
    form.setValue("placeOfBirth", `${city.city}, ${city.country}`, { shouldValidate: true });
    form.setValue("latitude", city.latitude.toString(), { shouldValidate: true });
    form.setValue("longitude", city.longitude.toString(), { shouldValidate: true });
    form.setValue("timezone", city.timezone, { shouldValidate: true });
    setCityOpen(false);
    setIsManualEntry(false);
  };

  const handleManualEntry = () => {
    setIsManualEntry(true);
    setCityOpen(false);
    toast({
      title: "Manual Entry Mode",
      description: "Please enter latitude, longitude, and timezone manually.",
    });
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
                      <Input placeholder="Enter full name" {...field} data-testid="input-name" />
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
                        data-testid="select-sex"
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
                        <Input type="date" {...field} data-testid="input-date" />
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
                        <Input type="time" step="1" {...field} data-testid="input-time" />
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
                  <FormItem className="flex flex-col">
                    <FormLabel>Place of Birth</FormLabel>
                    {isManualEntry ? (
                      <FormControl>
                        <Input
                          placeholder="Enter city, country"
                          {...field}
                          data-testid="input-place-manual"
                        />
                      </FormControl>
                    ) : (
                      <Popover open={cityOpen} onOpenChange={setCityOpen}>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              variant="outline"
                              role="combobox"
                              aria-expanded={cityOpen}
                              className={cn(
                                "w-full justify-between",
                                !field.value && "text-muted-foreground"
                              )}
                              data-testid="button-city-select"
                            >
                              {field.value || "Select city..."}
                              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-full p-0" align="start">
                          <Command>
                            <CommandInput
                              placeholder="Search cities..."
                              value={citySearch}
                              onValueChange={setCitySearch}
                              data-testid="input-city-search"
                            />
                            <CommandList>
                              <CommandEmpty>
                                <div className="p-2 text-center">
                                  <p className="text-sm text-muted-foreground mb-2">City not found</p>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={handleManualEntry}
                                    data-testid="button-manual-entry"
                                  >
                                    Enter coordinates manually
                                  </Button>
                                </div>
                              </CommandEmpty>
                              <CommandGroup>
                                {filteredCities.map((city) => (
                                  <CommandItem
                                    key={`${city.city}-${city.country}`}
                                    value={`${city.city}, ${city.country}`}
                                    onSelect={() => handleCitySelect(city)}
                                    data-testid={`city-option-${city.city.toLowerCase()}`}
                                  >
                                    <Check
                                      className={cn(
                                        "mr-2 h-4 w-4",
                                        field.value === `${city.city}, ${city.country}`
                                          ? "opacity-100"
                                          : "opacity-0"
                                      )}
                                    />
                                    {city.city}, {city.country}
                                  </CommandItem>
                                ))}
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
                    )}
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
                        <Input
                          type="number"
                          step="0.0001"
                          {...field}
                          disabled={!isManualEntry && !!field.value}
                          data-testid="input-latitude"
                        />
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
                        <Input
                          type="number"
                          step="0.0001"
                          {...field}
                          disabled={!isManualEntry && !!field.value}
                          data-testid="input-longitude"
                        />
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
                        <Input
                          {...field}
                          disabled={!isManualEntry && !!field.value}
                          data-testid="input-timezone"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {!isManualEntry && form.watch("latitude") && (
                <p className="text-xs text-muted-foreground">
                  Location auto-filled from city selection.{" "}
                  <button
                    type="button"
                    className="text-primary underline"
                    onClick={() => setIsManualEntry(true)}
                    data-testid="button-enable-manual"
                  >
                    Edit manually
                  </button>
                </p>
              )}
              {isManualEntry && (
                <p className="text-xs text-muted-foreground">
                  Manual entry mode.{" "}
                  <button
                    type="button"
                    className="text-primary underline"
                    onClick={() => setIsManualEntry(false)}
                    data-testid="button-use-city-select"
                  >
                    Use city selector
                  </button>
                </p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={createChartMutation.isPending}
              data-testid="button-generate-chart"
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

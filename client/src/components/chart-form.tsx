import { useForm } from "react-hook-form";
import { useState, useMemo } from "react";
import { Turnstile } from "@marsidev/react-turnstile";

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
  // INDIA - Major Cities
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
  {"city": "Visakhapatnam", "country": "India", "latitude": 17.6868, "longitude": 83.2185, "timezone": "Asia/Kolkata"},
  {"city": "Nagpur", "country": "India", "latitude": 21.1458, "longitude": 79.0882, "timezone": "Asia/Kolkata"},
  {"city": "Indore", "country": "India", "latitude": 22.7196, "longitude": 75.8577, "timezone": "Asia/Kolkata"},
  {"city": "Bhopal", "country": "India", "latitude": 23.2599, "longitude": 77.4126, "timezone": "Asia/Kolkata"},
  {"city": "Patna", "country": "India", "latitude": 25.5941, "longitude": 85.1376, "timezone": "Asia/Kolkata"},
  {"city": "Kanpur", "country": "India", "latitude": 26.4499, "longitude": 80.3319, "timezone": "Asia/Kolkata"},
  {"city": "Agra", "country": "India", "latitude": 27.1767, "longitude": 78.0081, "timezone": "Asia/Kolkata"},
  {"city": "Vadodara", "country": "India", "latitude": 22.3072, "longitude": 73.1812, "timezone": "Asia/Kolkata"},
  {"city": "Nashik", "country": "India", "latitude": 19.9975, "longitude": 73.7898, "timezone": "Asia/Kolkata"},
  {"city": "Rajkot", "country": "India", "latitude": 22.3039, "longitude": 70.8022, "timezone": "Asia/Kolkata"},
  {"city": "Tiruchirappalli", "country": "India", "latitude": 10.7905, "longitude": 78.7047, "timezone": "Asia/Kolkata"},
  {"city": "Salem", "country": "India", "latitude": 11.6643, "longitude": 78.1460, "timezone": "Asia/Kolkata"},
  {"city": "Tirunelveli", "country": "India", "latitude": 8.7139, "longitude": 77.7567, "timezone": "Asia/Kolkata"},
  {"city": "Mangalore", "country": "India", "latitude": 12.9141, "longitude": 74.8560, "timezone": "Asia/Kolkata"},
  {"city": "Vijayawada", "country": "India", "latitude": 16.5062, "longitude": 80.6480, "timezone": "Asia/Kolkata"},
  {"city": "Guwahati", "country": "India", "latitude": 26.1445, "longitude": 91.7362, "timezone": "Asia/Kolkata"},
  {"city": "Bhubaneswar", "country": "India", "latitude": 20.2961, "longitude": 85.8245, "timezone": "Asia/Kolkata"},
  {"city": "Ranchi", "country": "India", "latitude": 23.3441, "longitude": 85.3096, "timezone": "Asia/Kolkata"},
  {"city": "Raipur", "country": "India", "latitude": 21.2514, "longitude": 81.6296, "timezone": "Asia/Kolkata"},
  {"city": "Dehradun", "country": "India", "latitude": 30.3165, "longitude": 78.0322, "timezone": "Asia/Kolkata"},
  {"city": "Shimla", "country": "India", "latitude": 31.1048, "longitude": 77.1734, "timezone": "Asia/Kolkata"},
  {"city": "Udaipur", "country": "India", "latitude": 24.5854, "longitude": 73.7125, "timezone": "Asia/Kolkata"},
  {"city": "Jodhpur", "country": "India", "latitude": 26.2389, "longitude": 73.0243, "timezone": "Asia/Kolkata"},
  // USA - Major Cities  
  {"city": "New York", "country": "USA", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
  {"city": "Los Angeles", "country": "USA", "latitude": 34.0522, "longitude": -118.2437, "timezone": "America/Los_Angeles"},
  {"city": "Chicago", "country": "USA", "latitude": 41.8781, "longitude": -87.6298, "timezone": "America/Chicago"},
  {"city": "Houston", "country": "USA", "latitude": 29.7604, "longitude": -95.3698, "timezone": "America/Chicago"},
  {"city": "Phoenix", "country": "USA", "latitude": 33.4484, "longitude": -112.0740, "timezone": "America/Phoenix"},
  {"city": "Philadelphia", "country": "USA", "latitude": 39.9526, "longitude": -75.1652, "timezone": "America/New_York"},
  {"city": "San Antonio", "country": "USA", "latitude": 29.4241, "longitude": -98.4936, "timezone": "America/Chicago"},
  {"city": "San Diego", "country": "USA", "latitude": 32.7157, "longitude": -117.1611, "timezone": "America/Los_Angeles"},
  {"city": "San Francisco", "country": "USA", "latitude": 37.7749, "longitude": -122.4194, "timezone": "America/Los_Angeles"},
  {"city": "Seattle", "country": "USA", "latitude": 47.6062, "longitude": -122.3321, "timezone": "America/Los_Angeles"},
  {"city": "Boston", "country": "USA", "latitude": 42.3601, "longitude": -71.0589, "timezone": "America/New_York"},
  {"city": "Dallas", "country": "USA", "latitude": 32.7767, "longitude": -96.7970, "timezone": "America/Chicago"},
  {"city": "Austin", "country": "USA", "latitude": 30.2672, "longitude": -97.7431, "timezone": "America/Chicago"},
  {"city": "Denver", "country": "USA", "latitude": 39.7392, "longitude": -104.9903, "timezone": "America/Denver"},
  {"city": "Atlanta", "country": "USA", "latitude": 33.7490, "longitude": -84.3880, "timezone": "America/New_York"},
  {"city": "Miami", "country": "USA", "latitude": 25.7617, "longitude": -80.1918, "timezone": "America/New_York"},
  {"city": "Washington DC", "country": "USA", "latitude": 38.9072, "longitude": -77.0369, "timezone": "America/New_York"},
  {"city": "Las Vegas", "country": "USA", "latitude": 36.1699, "longitude": -115.1398, "timezone": "America/Los_Angeles"},
  {"city": "Portland", "country": "USA", "latitude": 45.5152, "longitude": -122.6784, "timezone": "America/Los_Angeles"},
  {"city": "San Jose", "country": "USA", "latitude": 37.3382, "longitude": -121.8863, "timezone": "America/Los_Angeles"},
  {"city": "Detroit", "country": "USA", "latitude": 42.3314, "longitude": -83.0458, "timezone": "America/Detroit"},
  {"city": "Minneapolis", "country": "USA", "latitude": 44.9778, "longitude": -93.2650, "timezone": "America/Chicago"},
  // UK & Ireland
  {"city": "London", "country": "UK", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
  {"city": "Manchester", "country": "UK", "latitude": 53.4808, "longitude": -2.2426, "timezone": "Europe/London"},
  {"city": "Birmingham", "country": "UK", "latitude": 52.4862, "longitude": -1.8904, "timezone": "Europe/London"},
  {"city": "Glasgow", "country": "UK", "latitude": 55.8642, "longitude": -4.2518, "timezone": "Europe/London"},
  {"city": "Edinburgh", "country": "UK", "latitude": 55.9533, "longitude": -3.1883, "timezone": "Europe/London"},
  {"city": "Liverpool", "country": "UK", "latitude": 53.4084, "longitude": -2.9916, "timezone": "Europe/London"},
  {"city": "Leeds", "country": "UK", "latitude": 53.8008, "longitude": -1.5491, "timezone": "Europe/London"},
  {"city": "Bristol", "country": "UK", "latitude": 51.4545, "longitude": -2.5879, "timezone": "Europe/London"},
  {"city": "Dublin", "country": "Ireland", "latitude": 53.3498, "longitude": -6.2603, "timezone": "Europe/Dublin"},
  {"city": "Belfast", "country": "UK", "latitude": 54.5973, "longitude": -5.9301, "timezone": "Europe/London"},
  // Canada
  {"city": "Toronto", "country": "Canada", "latitude": 43.6532, "longitude": -79.3832, "timezone": "America/Toronto"},
  {"city": "Vancouver", "country": "Canada", "latitude": 49.2827, "longitude": -123.1207, "timezone": "America/Vancouver"},
  {"city": "Montreal", "country": "Canada", "latitude": 45.5017, "longitude": -73.5673, "timezone": "America/Toronto"},
  {"city": "Calgary", "country": "Canada", "latitude": 51.0447, "longitude": -114.0719, "timezone": "America/Edmonton"},
  {"city": "Ottawa", "country": "Canada", "latitude": 45.4215, "longitude": -75.6972, "timezone": "America/Toronto"},
  {"city": "Edmonton", "country": "Canada", "latitude": 53.5461, "longitude": -113.4938, "timezone": "America/Edmonton"},
  {"city": "Winnipeg", "country": "Canada", "latitude": 49.8951, "longitude": -97.1384, "timezone": "America/Winnipeg"},
  // Australia & New Zealand
  {"city": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"},
  {"city": "Melbourne", "country": "Australia", "latitude": -37.8136, "longitude": 144.9631, "timezone": "Australia/Melbourne"},
  {"city": "Brisbane", "country": "Australia", "latitude": -27.4698, "longitude": 153.0251, "timezone": "Australia/Brisbane"},
  {"city": "Perth", "country": "Australia", "latitude": -31.9505, "longitude": 115.8605, "timezone": "Australia/Perth"},
  {"city": "Adelaide", "country": "Australia", "latitude": -34.9285, "longitude": 138.6007, "timezone": "Australia/Adelaide"},
  {"city": "Auckland", "country": "New Zealand", "latitude": -36.8485, "longitude": 174.7633, "timezone": "Pacific/Auckland"},
  {"city": "Wellington", "country": "New Zealand", "latitude": -41.2866, "longitude": 174.7756, "timezone": "Pacific/Auckland"},
  // Europe
  {"city": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone": "Europe/Paris"},
  {"city": "Berlin", "country": "Germany", "latitude": 52.5200, "longitude": 13.4050, "timezone": "Europe/Berlin"},
  {"city": "Munich", "country": "Germany", "latitude": 48.1351, "longitude": 11.5820, "timezone": "Europe/Berlin"},
  {"city": "Frankfurt", "country": "Germany", "latitude": 50.1109, "longitude": 8.6821, "timezone": "Europe/Berlin"},
  {"city": "Amsterdam", "country": "Netherlands", "latitude": 52.3676, "longitude": 4.9041, "timezone": "Europe/Amsterdam"},
  {"city": "Zurich", "country": "Switzerland", "latitude": 47.3769, "longitude": 8.5417, "timezone": "Europe/Zurich"},
  {"city": "Geneva", "country": "Switzerland", "latitude": 46.2044, "longitude": 6.1432, "timezone": "Europe/Zurich"},
  {"city": "Vienna", "country": "Austria", "latitude": 48.2082, "longitude": 16.3738, "timezone": "Europe/Vienna"},
  {"city": "Rome", "country": "Italy", "latitude": 41.9028, "longitude": 12.4964, "timezone": "Europe/Rome"},
  {"city": "Milan", "country": "Italy", "latitude": 45.4642, "longitude": 9.1900, "timezone": "Europe/Rome"},
  {"city": "Madrid", "country": "Spain", "latitude": 40.4168, "longitude": -3.7038, "timezone": "Europe/Madrid"},
  {"city": "Barcelona", "country": "Spain", "latitude": 41.3851, "longitude": 2.1734, "timezone": "Europe/Madrid"},
  {"city": "Lisbon", "country": "Portugal", "latitude": 38.7223, "longitude": -9.1393, "timezone": "Europe/Lisbon"},
  {"city": "Brussels", "country": "Belgium", "latitude": 50.8503, "longitude": 4.3517, "timezone": "Europe/Brussels"},
  {"city": "Copenhagen", "country": "Denmark", "latitude": 55.6761, "longitude": 12.5683, "timezone": "Europe/Copenhagen"},
  {"city": "Stockholm", "country": "Sweden", "latitude": 59.3293, "longitude": 18.0686, "timezone": "Europe/Stockholm"},
  {"city": "Oslo", "country": "Norway", "latitude": 59.9139, "longitude": 10.7522, "timezone": "Europe/Oslo"},
  {"city": "Helsinki", "country": "Finland", "latitude": 60.1699, "longitude": 24.9384, "timezone": "Europe/Helsinki"},
  {"city": "Warsaw", "country": "Poland", "latitude": 52.2297, "longitude": 21.0122, "timezone": "Europe/Warsaw"},
  {"city": "Prague", "country": "Czech Republic", "latitude": 50.0755, "longitude": 14.4378, "timezone": "Europe/Prague"},
  {"city": "Budapest", "country": "Hungary", "latitude": 47.4979, "longitude": 19.0402, "timezone": "Europe/Budapest"},
  {"city": "Athens", "country": "Greece", "latitude": 37.9838, "longitude": 23.7275, "timezone": "Europe/Athens"},
  {"city": "Moscow", "country": "Russia", "latitude": 55.7558, "longitude": 37.6173, "timezone": "Europe/Moscow"},
  {"city": "St Petersburg", "country": "Russia", "latitude": 59.9343, "longitude": 30.3351, "timezone": "Europe/Moscow"},
  // Asia Pacific
  {"city": "Singapore", "country": "Singapore", "latitude": 1.3521, "longitude": 103.8198, "timezone": "Asia/Singapore"},
  {"city": "Hong Kong", "country": "Hong Kong", "latitude": 22.3193, "longitude": 114.1694, "timezone": "Asia/Hong_Kong"},
  {"city": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
  {"city": "Osaka", "country": "Japan", "latitude": 34.6937, "longitude": 135.5023, "timezone": "Asia/Tokyo"},
  {"city": "Seoul", "country": "South Korea", "latitude": 37.5665, "longitude": 126.9780, "timezone": "Asia/Seoul"},
  {"city": "Busan", "country": "South Korea", "latitude": 35.1796, "longitude": 129.0756, "timezone": "Asia/Seoul"},
  {"city": "Beijing", "country": "China", "latitude": 39.9042, "longitude": 116.4074, "timezone": "Asia/Shanghai"},
  {"city": "Shanghai", "country": "China", "latitude": 31.2304, "longitude": 121.4737, "timezone": "Asia/Shanghai"},
  {"city": "Shenzhen", "country": "China", "latitude": 22.5431, "longitude": 114.0579, "timezone": "Asia/Shanghai"},
  {"city": "Guangzhou", "country": "China", "latitude": 23.1291, "longitude": 113.2644, "timezone": "Asia/Shanghai"},
  {"city": "Taipei", "country": "Taiwan", "latitude": 25.0330, "longitude": 121.5654, "timezone": "Asia/Taipei"},
  {"city": "Kuala Lumpur", "country": "Malaysia", "latitude": 3.1390, "longitude": 101.6869, "timezone": "Asia/Kuala_Lumpur"},
  {"city": "Bangkok", "country": "Thailand", "latitude": 13.7563, "longitude": 100.5018, "timezone": "Asia/Bangkok"},
  {"city": "Jakarta", "country": "Indonesia", "latitude": -6.2088, "longitude": 106.8456, "timezone": "Asia/Jakarta"},
  {"city": "Manila", "country": "Philippines", "latitude": 14.5995, "longitude": 120.9842, "timezone": "Asia/Manila"},
  {"city": "Ho Chi Minh City", "country": "Vietnam", "latitude": 10.8231, "longitude": 106.6297, "timezone": "Asia/Ho_Chi_Minh"},
  {"city": "Hanoi", "country": "Vietnam", "latitude": 21.0285, "longitude": 105.8542, "timezone": "Asia/Ho_Chi_Minh"},
  // Middle East
  {"city": "Dubai", "country": "UAE", "latitude": 25.2048, "longitude": 55.2708, "timezone": "Asia/Dubai"},
  {"city": "Abu Dhabi", "country": "UAE", "latitude": 24.4539, "longitude": 54.3773, "timezone": "Asia/Dubai"},
  {"city": "Doha", "country": "Qatar", "latitude": 25.2854, "longitude": 51.5310, "timezone": "Asia/Qatar"},
  {"city": "Riyadh", "country": "Saudi Arabia", "latitude": 24.7136, "longitude": 46.6753, "timezone": "Asia/Riyadh"},
  {"city": "Jeddah", "country": "Saudi Arabia", "latitude": 21.4858, "longitude": 39.1925, "timezone": "Asia/Riyadh"},
  {"city": "Kuwait City", "country": "Kuwait", "latitude": 29.3759, "longitude": 47.9774, "timezone": "Asia/Kuwait"},
  {"city": "Muscat", "country": "Oman", "latitude": 23.5880, "longitude": 58.3829, "timezone": "Asia/Muscat"},
  {"city": "Manama", "country": "Bahrain", "latitude": 26.2285, "longitude": 50.5860, "timezone": "Asia/Bahrain"},
  {"city": "Tel Aviv", "country": "Israel", "latitude": 32.0853, "longitude": 34.7818, "timezone": "Asia/Jerusalem"},
  {"city": "Amman", "country": "Jordan", "latitude": 31.9454, "longitude": 35.9284, "timezone": "Asia/Amman"},
  {"city": "Beirut", "country": "Lebanon", "latitude": 33.8938, "longitude": 35.5018, "timezone": "Asia/Beirut"},
  // South Asia
  {"city": "Colombo", "country": "Sri Lanka", "latitude": 6.9271, "longitude": 79.8612, "timezone": "Asia/Colombo"},
  {"city": "Dhaka", "country": "Bangladesh", "latitude": 23.8103, "longitude": 90.4125, "timezone": "Asia/Dhaka"},
  {"city": "Kathmandu", "country": "Nepal", "latitude": 27.7172, "longitude": 85.3240, "timezone": "Asia/Kathmandu"},
  {"city": "Karachi", "country": "Pakistan", "latitude": 24.8607, "longitude": 67.0011, "timezone": "Asia/Karachi"},
  {"city": "Lahore", "country": "Pakistan", "latitude": 31.5204, "longitude": 74.3587, "timezone": "Asia/Karachi"},
  {"city": "Islamabad", "country": "Pakistan", "latitude": 33.6844, "longitude": 73.0479, "timezone": "Asia/Karachi"},
  // Africa
  {"city": "Cairo", "country": "Egypt", "latitude": 30.0444, "longitude": 31.2357, "timezone": "Africa/Cairo"},
  {"city": "Cape Town", "country": "South Africa", "latitude": -33.9249, "longitude": 18.4241, "timezone": "Africa/Johannesburg"},
  {"city": "Johannesburg", "country": "South Africa", "latitude": -26.2041, "longitude": 28.0473, "timezone": "Africa/Johannesburg"},
  {"city": "Lagos", "country": "Nigeria", "latitude": 6.5244, "longitude": 3.3792, "timezone": "Africa/Lagos"},
  {"city": "Nairobi", "country": "Kenya", "latitude": -1.2921, "longitude": 36.8219, "timezone": "Africa/Nairobi"},
  {"city": "Casablanca", "country": "Morocco", "latitude": 33.5731, "longitude": -7.5898, "timezone": "Africa/Casablanca"},
  // South America
  {"city": "Sao Paulo", "country": "Brazil", "latitude": -23.5505, "longitude": -46.6333, "timezone": "America/Sao_Paulo"},
  {"city": "Rio de Janeiro", "country": "Brazil", "latitude": -22.9068, "longitude": -43.1729, "timezone": "America/Sao_Paulo"},
  {"city": "Buenos Aires", "country": "Argentina", "latitude": -34.6037, "longitude": -58.3816, "timezone": "America/Argentina/Buenos_Aires"},
  {"city": "Santiago", "country": "Chile", "latitude": -33.4489, "longitude": -70.6693, "timezone": "America/Santiago"},
  {"city": "Lima", "country": "Peru", "latitude": -12.0464, "longitude": -77.0428, "timezone": "America/Lima"},
  {"city": "Bogota", "country": "Colombia", "latitude": 4.7110, "longitude": -74.0721, "timezone": "America/Bogota"},
  {"city": "Mexico City", "country": "Mexico", "latitude": 19.4326, "longitude": -99.1332, "timezone": "America/Mexico_City"},
  {"city": "Guadalajara", "country": "Mexico", "latitude": 20.6597, "longitude": -103.3496, "timezone": "America/Mexico_City"},
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

const TURNSTILE_SITE_KEY = "0x4AAAAAACuBMk9QffkMSOPv"; // Cloudflare test key (always passes)

export function ChartForm({ onSuccess }: ChartFormProps) {
  const { toast } = useToast();
  const [cityOpen, setCityOpen] = useState(false);
  const [citySearch, setCitySearch] = useState("");
  const [isManualEntry, setIsManualEntry] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

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

  // Default list shown before the user types (popular cities for this app's audience).
  const DEFAULT_CITIES = CITIES_LOV.slice(0, 10);

  const filteredCities = useMemo(() => {
    if (!citySearch || citySearch.length < 2) return DEFAULT_CITIES;
    const lower = citySearch.toLowerCase();
    return CITIES_LOV.filter(
      (c) =>
        c.city.toLowerCase().includes(lower) ||
        c.country.toLowerCase().includes(lower)
    ).slice(0, 15);
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
        turnstile_token: turnstileToken,
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
                              {field.value || "Search for a city worldwide..."}
                              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-full p-0" align="start">
                          <Command shouldFilter={false}>
                            <CommandInput
                              placeholder="Search city (e.g., Chennai, London, New York)..."
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
                              <CommandGroup
                                heading={!citySearch || citySearch.length < 2 ? "Popular cities" : "Results"}
                              >
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

            {/* CAPTCHA */}
            <div className="flex justify-center">
              <Turnstile
                siteKey={TURNSTILE_SITE_KEY}
                onSuccess={(token) => setTurnstileToken(token)}
                onExpire={() => setTurnstileToken(null)}
                onError={() => setTurnstileToken(null)}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={createChartMutation.isPending || !turnstileToken}
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

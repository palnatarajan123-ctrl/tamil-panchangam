import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Code, Calculator, Globe } from "lucide-react";

export default function Docs() {
  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-primary" />
          Documentation
        </h1>
        <p className="text-muted-foreground">
          Technical reference for the Tamil Panchangam Astrology Engine.
        </p>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Calculation Method
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              This engine uses <strong>Drik Ganita</strong> (observational/modern astronomical calculations) 
              as opposed to Surya Siddhanta or other traditional methods. This provides accuracy 
              matching modern astronomical software.
            </p>
            <h4>Key Characteristics:</h4>
            <ul>
              <li>Swiss Ephemeris for planetary calculations</li>
              <li>Precision to arc-seconds for planetary positions</li>
              <li>Accurate sunrise/sunset calculations for local horizon</li>
              <li>Dynamic ayanamsa calculation (not fixed offset)</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Lahiri Ayanamsa
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <p>
              <strong>Lahiri Ayanamsa</strong> (also known as Chitrapaksha Ayanamsa) is the 
              official ayanamsa adopted by the Indian government and is the most widely 
              used in South India.
            </p>
            <h4>Definition:</h4>
            <p>
              The ayanamsa is calibrated such that the star Spica (Chitra) is at exactly 
              0° Libra (180° from the vernal equinox in the sidereal zodiac).
            </p>
            <h4>Current Value:</h4>
            <p className="font-mono">
              Approximately 24° 10' as of 2024 (increases by ~50.3" per year)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              API Reference
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h4 className="font-semibold mb-2">Health Check</h4>
              <div className="bg-muted/50 p-3 rounded-md font-mono text-sm">
                GET /api/health
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Returns service status, ayanamsa type, and calculation method.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Create Birth Chart</h4>
              <div className="bg-muted/50 p-3 rounded-md font-mono text-sm">
                POST /api/base-chart/create
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Creates an immutable birth chart from provided birth details.
              </p>
              <pre className="bg-muted/50 p-3 rounded-md font-mono text-xs mt-2 overflow-x-auto">
{`{
  "name": "string",
  "date_of_birth": "YYYY-MM-DD",
  "time_of_birth": "HH:MM:SS",
  "place_of_birth": "string",
  "latitude": number,
  "longitude": number,
  "timezone": "string"
}`}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">List Charts</h4>
              <div className="bg-muted/50 p-3 rounded-md font-mono text-sm">
                GET /api/base-chart/list
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Returns all stored birth charts.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Generate Monthly Prediction</h4>
              <div className="bg-muted/50 p-3 rounded-md font-mono text-sm">
                POST /api/prediction/monthly
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Generates transit-based predictions for specified months.
              </p>
              <pre className="bg-muted/50 p-3 rounded-md font-mono text-xs mt-2 overflow-x-auto">
{`{
  "base_chart_id": "string",
  "year": number,
  "months": [number]
}`}
              </pre>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Architecture</CardTitle>
            <CardDescription>
              Service separation for data integrity
            </CardDescription>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <h4>Two-Service Model:</h4>
            <ol>
              <li>
                <strong>Base Chart Service</strong>: Computes and stores immutable birth chart data.
                Once created, a base chart is never recomputed.
              </li>
              <li>
                <strong>Prediction Service</strong>: Generates temporal predictions by consuming
                stored base chart data. Recomputed for each prediction request.
              </li>
            </ol>
            <p>
              This separation ensures astronomical truth (the birth chart) remains constant,
              while interpretive predictions can be regenerated as needed.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

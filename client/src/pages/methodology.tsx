import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { ArrowLeft, BookOpen, Calculator, Shield, AlertTriangle } from "lucide-react";

export default function MethodologyPage() {
  return (
    <div className="container max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/">
          <Button variant="ghost" size="icon" data-testid="button-back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-serif font-semibold tracking-tight flex items-center gap-3">
            <BookOpen className="h-7 w-7 text-primary" />
            Methodology
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            How calculations are performed
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <Card className="border-muted" data-testid="card-calculation-standards">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Calculation Standards
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Ephemeris Source</h4>
              <p className="text-sm text-muted-foreground">
                All planetary positions are calculated using Swiss Ephemeris, the industry-standard 
                astronomical library used by professional astrology software worldwide. Swiss Ephemeris 
                provides sub-arc-second precision for planetary longitudes.
              </p>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Ayanamsa</h4>
              <p className="text-sm text-muted-foreground">
                This system uses Lahiri Ayanamsa (Chitrapaksha), the official ayanamsa adopted by 
                the Government of India for calendar calculations.
              </p>
            </div>

            <div>
              <h4 className="font-medium mb-2">Node Calculation</h4>
              <p className="text-sm text-muted-foreground">
                Mean Node is used by default for Rahu and Ketu, following traditional Tamil/South 
                Indian astrology conventions.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-muted" data-testid="card-divisional-charts">
          <CardHeader>
            <CardTitle>Divisional Charts (Vargas)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              All divisional charts follow the Classical Parashara method as described in 
              Brihat Parashara Hora Shastra:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {[
                { id: "D1", name: "Rasi", purpose: "Core chart" },
                { id: "D2", name: "Hora", purpose: "Wealth" },
                { id: "D7", name: "Saptamsa", purpose: "Creativity" },
                { id: "D9", name: "Navamsa", purpose: "Dharma" },
                { id: "D10", name: "Dasamsa", purpose: "Career" },
              ].map((chart) => (
                <div key={chart.id} className="bg-muted/50 p-3 rounded-md text-center">
                  <Badge variant="outline" className="mb-1">{chart.id}</Badge>
                  <div className="text-sm font-medium">{chart.name}</div>
                  <div className="text-xs text-muted-foreground">{chart.purpose}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-muted" data-testid="card-scoring">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Scoring & Synthesis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Deterministic Scoring</h4>
              <p className="text-sm text-muted-foreground">
                All life-area scores are computed using deterministic algorithms based on Dasha/Bhukti 
                influences, Gochara effects, Ashtakavarga, house strength, and Yoga formations. 
                The same input always produces the same output.
              </p>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">AI Interpretation</h4>
              <p className="text-sm text-muted-foreground">
                The AI language model is used exclusively for language generation. It receives 
                pre-computed scores and ranked signals, but does NOT perform any astrological 
                calculations or see raw planetary degrees.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-500/30 bg-amber-500/5" data-testid="card-cusp-sensitivity">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5" />
              Cusp & Boundary Sensitivity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              For fast-moving celestial bodies (Moon, Mercury, Venus, Ascendant), placements very 
              close to sign or divisional boundaries may vary slightly across traditions or software due to:
            </p>
            <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
              <li>Minor differences in ayanamsa calculation</li>
              <li>Rounding approaches at boundaries</li>
              <li>Birth time precision limitations</li>
            </ul>
            
            <div className="bg-background/50 p-3 rounded-md mt-4">
              <h5 className="font-medium text-sm mb-2">How This System Handles Cusps</h5>
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                <li>Logs planetary longitude to arc-second precision</li>
                <li>Uses deterministic boundary rules (no auto-adjustment)</li>
                <li>Does NOT round degrees before computing divisions</li>
              </ul>
            </div>

            <p className="text-xs text-muted-foreground italic mt-4">
              For birth times known only to the nearest hour, the Ascendant moves approximately 
              1 degree every 4 minutes. A 15-minute uncertainty creates approximately 4 degrees 
              of Ascendant uncertainty — enough to shift the Lagna to an adjacent sign.
            </p>
          </CardContent>
        </Card>

        <Card className="border-muted" data-testid="card-reproducibility">
          <CardHeader>
            <CardTitle>Reproducibility Guarantee</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Given identical inputs (date of birth, time of birth, geographic coordinates, 
              and node type selection), this system will produce identical outputs on any date, 
              on any device, indefinitely. All calculations are versioned and archived for 
              audit purposes.
            </p>
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground text-center mt-8">
        This methodology document is static and is not generated by AI.
      </p>
    </div>
  );
}

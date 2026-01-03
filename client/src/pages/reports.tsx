import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download, Eye } from "lucide-react";
import { StatusBadge } from "@/components/status-badge";

export default function Reports() {
  return (
    <div className="container max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-2 mb-8">
        <h1 className="text-3xl font-serif font-bold flex items-center gap-3">
          <FileText className="h-8 w-8 text-primary" />
          Report Builder
        </h1>
        <p className="text-muted-foreground">
          Generate comprehensive PDF reports from birth charts and predictions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  Report Preview
                </span>
                <StatusBadge status="stub" />
              </CardTitle>
              <CardDescription>
                Live preview of your generated report
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="aspect-[8.5/11] bg-muted/30 rounded-md border-2 border-dashed flex items-center justify-center">
                <div className="text-center space-y-4 p-8">
                  <FileText className="h-16 w-16 mx-auto opacity-20" />
                  <div>
                    <p className="text-muted-foreground">PDF Preview</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Report generation pending implementation
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Report Options</CardTitle>
              <CardDescription>
                Customize your report content
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Include Sections</h4>
                <div className="space-y-2">
                  {[
                    "Birth Chart (D1 Rasi)",
                    "Navamsa Chart (D9)",
                    "Planetary Positions",
                    "Nakshatra Details",
                    "Panchangam",
                    "Vimshottari Dasha",
                    "Monthly Transits",
                    "Pancha Pakshi",
                  ].map((section, index) => (
                    <label
                      key={index}
                      className="flex items-center gap-3 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="rounded border-input"
                        defaultChecked
                        disabled
                        data-testid={`checkbox-section-${index}`}
                      />
                      <span className="text-muted-foreground">{section}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Export</CardTitle>
              <CardDescription>
                Download your completed report
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full gap-2" disabled data-testid="button-download-pdf">
                <Download className="h-4 w-4" />
                Download PDF
              </Button>
              <Button variant="outline" className="w-full gap-2" disabled data-testid="button-print">
                <FileText className="h-4 w-4" />
                Print Report
              </Button>
              <p className="text-xs text-muted-foreground text-center mt-2">
                Report generation requires a completed birth chart
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface BirthReference {
  janmaNakshatra: string | null;
  janmaRasi: string | null;
  lagna: string | null;
  moonSign: string | null;
  nakshatraLord: string | null;
  birthDasha: string | null;
}

interface ActiveDashaContext {
  currentMahadasha: string | null;
  currentAntardasha: string | null;
  dashaBalance: string | null;
  yogakarakaPlanets: string[];
  functionalRoleSummary: string | null;
}

interface TransitContext {
  jupiterTransit: string | null;
  saturnTransit: string | null;
  rahuKetuAxis: string | null;
}

interface NakshatraTimingContext {
  currentMoonNakshatra: string | null;
  taraBala: string | null;
  chandraGati: string | null;
  favorableWindow: string | null;
}

interface PakshiContext {
  dominantPakshi: string | null;
  activityPhase: string | null;
}

export interface BirthAstroContextData {
  birthReference: BirthReference;
  activeDashaContext: ActiveDashaContext;
  transitContext: TransitContext;
  nakshatraTimingContext: NakshatraTimingContext;
  pakshiContext: PakshiContext;
}

interface Props {
  data: BirthAstroContextData;
}

function ContextRow({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | null;
  highlight?: boolean;
}) {
  return (
    <TableRow>
      <TableCell className="font-medium text-muted-foreground w-1/2">
        {label}
      </TableCell>
      <TableCell className={highlight ? "font-semibold text-primary" : ""}>
        {value ?? "—"}
      </TableCell>
    </TableRow>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <TableRow className="bg-muted/30">
      <TableCell colSpan={2} className="py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
      </TableCell>
    </TableRow>
  );
}

export function BirthAstroContextTable({ data }: Props) {
  const { 
    birthReference, 
    activeDashaContext, 
    transitContext, 
    nakshatraTimingContext,
    pakshiContext,
  } = data;

  return (
    <Card className="border-muted" data-testid="card-birth-astro-context">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          Astrological Context
          <Badge variant="outline" className="text-xs font-normal">
            Birth + Current
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableBody>
            <SectionHeader title="Birth Reference" />
            <ContextRow 
              label="Janma Nakshatra" 
              value={birthReference.janmaNakshatra}
              highlight
            />
            <ContextRow label="Janma Rasi" value={birthReference.janmaRasi} />
            <ContextRow label="Lagna" value={birthReference.lagna} />
            <ContextRow label="Moon Sign" value={birthReference.moonSign} />
            <ContextRow label="Nakshatra Lord" value={birthReference.nakshatraLord} />
            <ContextRow label="Birth Dasha" value={birthReference.birthDasha} />

            <SectionHeader title="Active Dasha Context (Now)" />
            <ContextRow 
              label="Current Mahadasha" 
              value={activeDashaContext.currentMahadasha}
              highlight
            />
            <ContextRow 
              label="Current Antardasha" 
              value={activeDashaContext.currentAntardasha}
            />
            <ContextRow label="Dasha Balance" value={activeDashaContext.dashaBalance} />
            <ContextRow 
              label="Functional Role Planets" 
              value={activeDashaContext.functionalRoleSummary}
            />

            <SectionHeader title="Transit / Gochara Context" />
            <ContextRow label="Jupiter Transit" value={transitContext.jupiterTransit} />
            <ContextRow label="Saturn Transit" value={transitContext.saturnTransit} />
            <ContextRow label="Rahu–Ketu Axis" value={transitContext.rahuKetuAxis} />

            <SectionHeader title="Nakshatra & Timing Context" />
            <ContextRow 
              label="Current Moon Nakshatra" 
              value={nakshatraTimingContext.currentMoonNakshatra}
            />
            <ContextRow label="Tara Bala" value={nakshatraTimingContext.taraBala} />
            <ContextRow label="Chandra Gati" value={nakshatraTimingContext.chandraGati} />
            <ContextRow 
              label="Favorable Window" 
              value={nakshatraTimingContext.favorableWindow}
            />

            <SectionHeader title="Pakshi / Rhythm Context" />
            <ContextRow label="Dominant Pakshi" value={pakshiContext.dominantPakshi} />
            <ContextRow label="Activity Phase" value={pakshiContext.activityPhase} />
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export interface RealtimeContextData {
  transit_context?: {
    jupiter_transit?: string | null;
    saturn_transit?: string | null;
    rahu_ketu_axis?: string | null;
  };
  nakshatra_timing_context?: {
    current_moon_nakshatra?: string | null;
    tara_bala?: string | null;
    chandra_gati?: string | null;
    favorable_window?: string | null;
  };
  pakshi_context?: {
    dominant_pakshi?: string | null;
    activity_phase?: string | null;
  };
}

export function adaptBirthChartToAstroContext(
  birthChartUI: any,
  predictionEnvelope?: any,
  realtimeContext?: RealtimeContextData
): BirthAstroContextData {
  const moonNakshatra = findMoonNakshatra(birthChartUI.nakshatra);
  const moonRasi = findMoonRasi(birthChartUI.rasi);

  const birthReference: BirthReference = {
    janmaNakshatra: moonNakshatra,
    janmaRasi: moonRasi,
    lagna: getLagnaRasiName(birthChartUI.southIndianChart?.lagna),
    moonSign: moonRasi,
    nakshatraLord: getNakshatraLord(moonNakshatra),
    birthDasha: formatBirthDasha(birthChartUI.vimshottari),
  };

  const activeDashaContext: ActiveDashaContext = extractDashaContext(
    birthChartUI.vimshottari,
    predictionEnvelope?.dasha_context,
    birthChartUI.functional_roles ?? predictionEnvelope?.functional_roles
  );

  let transitContext: TransitContext;
  if (realtimeContext?.transit_context) {
    transitContext = {
      jupiterTransit: realtimeContext.transit_context.jupiter_transit ?? null,
      saturnTransit: realtimeContext.transit_context.saturn_transit ?? null,
      rahuKetuAxis: realtimeContext.transit_context.rahu_ketu_axis ?? null,
    };
  } else {
    transitContext = extractTransitContext(predictionEnvelope?.transits);
  }

  let nakshatraTimingContext: NakshatraTimingContext;
  if (realtimeContext?.nakshatra_timing_context) {
    nakshatraTimingContext = {
      currentMoonNakshatra: realtimeContext.nakshatra_timing_context.current_moon_nakshatra ?? null,
      taraBala: realtimeContext.nakshatra_timing_context.tara_bala ?? null,
      chandraGati: realtimeContext.nakshatra_timing_context.chandra_gati ?? null,
      favorableWindow: realtimeContext.nakshatra_timing_context.favorable_window ?? null,
    };
  } else {
    nakshatraTimingContext = extractNakshatraContext(
      predictionEnvelope?.nakshatra_context,
      predictionEnvelope?.chandra_gati
    );
  }

  let pakshiContext: PakshiContext;
  if (realtimeContext?.pakshi_context) {
    pakshiContext = {
      dominantPakshi: realtimeContext.pakshi_context.dominant_pakshi ?? null,
      activityPhase: realtimeContext.pakshi_context.activity_phase ?? null,
    };
  } else {
    pakshiContext = extractPakshiContext(predictionEnvelope?.pakshi);
  }

  return {
    birthReference,
    activeDashaContext,
    transitContext,
    nakshatraTimingContext,
    pakshiContext,
  };
}

function findMoonNakshatra(nakshatraList: any[]): string | null {
  if (!nakshatraList) return null;
  const moonEntry = nakshatraList.find((n) =>
    n.planets?.includes("Moon")
  );
  return moonEntry?.name ?? null;
}

function findMoonRasi(rasiList: any[]): string | null {
  if (!rasiList) return null;
  const moonEntry = rasiList.find((r) =>
    r.planets?.includes("Moon")
  );
  return moonEntry?.name ?? null;
}

const RASI_ORDER = [
  "Mesham", "Rishabam", "Mithunam", "Kadakam",
  "Simmam", "Kanni", "Thulam", "Vrischikam",
  "Dhanusu", "Makaram", "Kumbham", "Meenam",
];

function getLagnaRasiName(lagnaIndex: number | undefined): string | null {
  if (lagnaIndex === undefined || lagnaIndex < 0 || lagnaIndex >= 12) {
    return null;
  }
  return RASI_ORDER[lagnaIndex];
}

const NAKSHATRA_LORDS: Record<string, string> = {
  "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun",
  "Rohini": "Moon", "Mrigashira": "Mars", "Ardra": "Rahu",
  "Punarvasu": "Jupiter", "Pushya": "Saturn", "Ashlesha": "Mercury",
  "Magha": "Ketu", "Purva Phalguni": "Venus", "Uttara Phalguni": "Sun",
  "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
  "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
  "Mula": "Ketu", "Purva Ashadha": "Venus", "Uttara Ashadha": "Sun",
  "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
  "Purva Bhadrapada": "Jupiter", "Uttara Bhadrapada": "Saturn", "Revati": "Mercury",
};

function getNakshatraLord(nakshatra: string | null): string | null {
  if (!nakshatra) return null;
  return NAKSHATRA_LORDS[nakshatra] ?? null;
}

function formatBirthDasha(vimshottari: any): string | null {
  const timeline = vimshottari?.timeline;
  if (!timeline || timeline.length === 0) return null;
  
  const first = timeline[0];
  return first?.mahadasha ?? null;
}

function extractDashaContext(
  vimshottari: any,
  dashaContext?: any,
  functionalRoles?: any
): ActiveDashaContext {
  const current = vimshottari?.current;
  const mahaLord = dashaContext?.maha_lord ?? current?.lord ?? null;
  const antarLord = dashaContext?.antar_lord ?? current?.antar?.lord ?? null;

  let dashaBalance: string | null = null;
  if (current?.end) {
    const endDate = new Date(current.end);
    const now = new Date();
    const totalDays = Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    if (totalDays > 0) {
      const years = Math.floor(totalDays / 365);
      const months = Math.floor((totalDays % 365) / 30);
      dashaBalance = `${years}y ${months}m remaining`;
    }
  }

  const yogakarakas = functionalRoles?.summary?.yogakarakas 
    ?? functionalRoles?.summary?.classical_yogakarakas 
    ?? [];
  
  const benefics = functionalRoles?.summary?.functional_benefics ?? functionalRoles?.summary?.benefics ?? [];
  const malefics = functionalRoles?.summary?.functional_malefics ?? functionalRoles?.summary?.malefics ?? [];
  const lagnaName = functionalRoles?.lagna?.name ?? null;
  
  let functionalRoleSummary: string | null = null;
  if (yogakarakas.length > 0) {
    functionalRoleSummary = `Yogakaraka: ${yogakarakas.join(", ")}`;
  } else if (benefics.length > 0) {
    functionalRoleSummary = `Benefics: ${benefics.join(", ")}`;
  } else if (lagnaName) {
    functionalRoleSummary = `${lagnaName} lagna (no classical yogakaraka)`;
  }

  return {
    currentMahadasha: mahaLord,
    currentAntardasha: antarLord,
    dashaBalance,
    yogakarakaPlanets: yogakarakas,
    functionalRoleSummary,
  };
}

function extractTransitContext(transits?: any): TransitContext {
  if (!transits) {
    return {
      jupiterTransit: null,
      saturnTransit: null,
      rahuKetuAxis: null,
    };
  }

  const jupiter = transits.planets?.Jupiter;
  const saturn = transits.planets?.Saturn;
  const rahu = transits.planets?.Rahu;
  const ketu = transits.planets?.Ketu;

  return {
    jupiterTransit: jupiter
      ? `${jupiter.current_rasi} (House ${jupiter.house_from_moon})`
      : null,
    saturnTransit: saturn
      ? `${saturn.current_rasi} (House ${saturn.house_from_moon})`
      : null,
    rahuKetuAxis: rahu && ketu
      ? `${rahu.current_rasi} / ${ketu.current_rasi}`
      : null,
  };
}

function extractNakshatraContext(
  nakshatraContext?: any,
  chandraGati?: any
): NakshatraTimingContext {
  return {
    currentMoonNakshatra: nakshatraContext?.current_moon_nakshatra ?? null,
    taraBala: nakshatraContext?.tara_bala?.classification ?? null,
    chandraGati: chandraGati?.dominant_mood ?? null,
    favorableWindow: nakshatraContext?.favorable_window ?? null,
  };
}

function extractPakshiContext(pakshi?: any): PakshiContext {
  return {
    dominantPakshi: pakshi?.pakshi ?? pakshi?.birth_pakshi ?? null,
    activityPhase: pakshi?.activity ?? pakshi?.current_activity ?? null,
  };
}

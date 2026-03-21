// client/src/adapters/birthChartAdapter.ts

/* ============================================================
   Canonical Rāsi Order (Tamil — matches backend D1 keys)
   ============================================================ */

const RASI_ORDER = [
  "Mesham",
  "Rishabam",
  "Mithunam",
  "Kadakam",
  "Simmam",
  "Kanni",
  "Thulam",
  "Vrischikam",
  "Dhanusu",
  "Makaram",
  "Kumbham",
  "Meenam",
];

function rasiToIndex(rasi?: string): number {
  if (!rasi) return 0;
  const idx = RASI_ORDER.indexOf(rasi);
  return idx >= 0 ? idx : 0;
}

/* ============================================================
   UI Model Contracts
   ============================================================ */

interface ChartData {
  lagna: number;
  planets: Record<string, number>;
  dignity?: Record<string, "exalted" | "debilitated" | "neutral">;
}

export interface BirthChartUIModel {
  identity: {
    name: string;
    place: string;
  };

  birth: {
    date: string;
    time: string;
  };

  southIndianChart: {
    lagna: number;
    planets: Record<string, number>;
  };

  navamsaChart: {
    lagna: number;
    planets: Record<string, number>;
    dignity: Record<string, "exalted" | "debilitated" | "neutral">;
  };

  divisionalCharts: {
    D1: ChartData;
    D2?: ChartData;
    D7?: ChartData;
    D9: ChartData;
    D10?: ChartData;
  };

  chartMetadata?: {
    ayanamsa: string;
    division_method: string;
    precision: string;
    node_type: string;
  };

  rasi: Array<{
    name: string;
    planets: string[];
  }>;

  nakshatra: Array<{
    name: string;
    planets: string[];
  }>;

  houses: Array<{
    number: number;
    rasi: string;
    lord: string;
    significations: string;
    planets: string[];
  }>;

  vimshottari: {
    timeline: {
      mahadasha: string;
      start: string;
      end: string;
      is_partial: boolean;
      antar_dashas?: any[];
    }[];
    current: {
      lord: string;
      start: string;
      end: string;
      is_partial: boolean;
      antar?: {
        lord: string;
        start: string;
        end: string;
        confidence_weight?: number;
      } | null;
    } | null;
  };

  functional_roles?: {
    lagna?: { rasi?: number; name?: string };
    planets?: Record<string, any>;
    summary?: {
      functional_benefics?: string[];
      functional_malefics?: string[];
      neutrals?: string[];
      yogakarakas?: string[];
      classical_yogakarakas?: string[];
      marakas?: string[];
    };
  };

  yogas?: {
    yogas: Array<{
      name: string;
      present: boolean;
      strength: string;
      effects: string[];
      rationale: string;
      category?: string;
      planet?: string;
      planets?: string[];
      placement?: string;
      house?: number;
      moon_house?: number;
      type?: string;
    }>;
    summary: {
      total_yogas: number;
      has_gaja_kesari: boolean;
      has_dhana_yoga: boolean;
      has_raja_yoga: boolean;
      has_pancha_mahapurusha: boolean;
      has_budhaditya: boolean;
      has_kemadruma: boolean;
      yoga_names: string[];
    };
  };

  sade_sati?: {
    moon_sign: number;
    moon_sign_name: string;
    current_saturn_sign: number | null;
    current_saturn_sign_name: string;
    saturn_house_from_moon: number | null;
    reference_date: string;
    alert_level: "high" | "medium" | "low" | "unknown";
    sade_sati: {
      active: boolean;
      phase: number | null;
      phase_name: string | null;
      effects: string[];
      remedies: string[];
      current_phase_ends: string | null;
      all_windows: Array<{
        phase: number;
        phase_name: string;
        saturn_sign: number;
        saturn_sign_name: string;
        start_date: string;
        end_date: string;
      }>;
      summary: string;
    };
    ashtama_shani: {
      active: boolean;
      effects: string[];
      remedies: string[];
      ends: string | null;
      summary: string;
    };
    kantaka_shani: {
      active: boolean;
      effects: string[];
      ends: string | null;
      summary: string;
    };
    error: string | null;
  };

  shadbala?: {
    planets: Record<string, {
      total_shashtiamsas: number;
      rupas: number;
      percent_strength: number;
      strength_label: "Very Strong" | "Strong" | "Moderate" | "Weak";
      components: {
        sthana_bala: { score: number; placement: string; house: number };
        dig_bala: { score: number; peak_house: number; house: number };
        chesta_bala: { score: number; motion: string };
        naisargika_bala: { score: number };
        drik_bala: { score: number };
      };
      is_retrograde: boolean;
      sign: number;
      house: number;
    }>;
    ranking: string[];
    strongest_planet: string | null;
    weakest_planet: string | null;
    summary: {
      strongest: string | null;
      weakest: string | null;
      very_strong_count: number;
      weak_count: number;
    };
    error: string | null;
  };
}

/* ============================================================
   Helpers
   ============================================================ */

/**
 * Convert D1/D9 chart objects → planet → rasiIndex
 */
function mapChartToPlanets(chart: Record<string, any>) {
  const out: Record<string, number> = {};

  Object.entries(chart ?? {}).forEach(([rasi, planets]) => {
    if (!Array.isArray(planets)) return;

    const rasiIndex = rasiToIndex(rasi);
    planets.forEach((planet) => {
      out[planet] = rasiIndex;
    });
  });

  return out;
}

const ENGLISH_TO_TAMIL: Record<string, string> = {
  Aries: "Mesham",
  Taurus: "Rishabam",
  Gemini: "Mithunam",
  Cancer: "Kadakam",
  Leo: "Simmam",
  Virgo: "Kanni",
  Libra: "Thulam",
  Scorpio: "Vrischikam",
  Sagittarius: "Dhanusu",
  Capricorn: "Makaram",
  Aquarius: "Kumbham",
  Pisces: "Meenam",
};

/**
 * Convert Navamsa structure → usable UI maps
 * Handles both legacy format { planet: { sign, dignity } }
 * and new format { planets: { planet: { sign, dignity } } }
 */
function adaptNavamsa(divisionalCharts: any) {
  const d9Raw = divisionalCharts?.D9 ?? {};
  
  // Support new format with planets wrapper OR legacy direct format
  const d9 = d9Raw?.planets ?? d9Raw;

  const planets: Record<string, number> = {};
  const dignity: Record<
    string,
    "exalted" | "debilitated" | "neutral"
  > = {};

  Object.entries(d9).forEach(([planet, data]: any) => {
    // Skip metadata fields
    if (planet === "metadata" || planet === "lagna") return;
    
    const sign = data?.navamsa_sign || data?.sign;
    if (!sign) return;

    const tamilIndex = rasiToIndex(ENGLISH_TO_TAMIL[sign] || sign);
    planets[planet] = tamilIndex;
    dignity[planet] = data?.dignity ?? "neutral";
  });

  return {
    lagna: 0,
    planets,
    dignity,
  };
}

/**
 * Adapt any divisional chart (D2, D7, D10) to UI format
 */
function adaptDivisionalChart(chartData: any): ChartData {
  const planets: Record<string, number> = {};
  const dignity: Record<string, "exalted" | "debilitated" | "neutral"> = {};

  if (!chartData?.planets) {
    return { lagna: 0, planets: {}, dignity: {} };
  }

  Object.entries(chartData.planets).forEach(([planet, data]: any) => {
    const sign = data?.sign;
    if (!sign) return;

    const tamilIndex = rasiToIndex(ENGLISH_TO_TAMIL[sign] || sign);
    planets[planet] = tamilIndex;
    if (data?.dignity) {
      dignity[planet] = data.dignity;
    }
  });

  return {
    lagna: 0,
    planets,
    dignity: Object.keys(dignity).length > 0 ? dignity : undefined,
  };
}

/* ============================================================
   Adapter Entry Point
   ============================================================ */

export function adaptBirthChart(raw: any): BirthChartUIModel {
  const view = raw.view ?? raw;

  /* ---------------- D1: Planet → Rāsi Index ---------------- */

  const planetsByRasiIndex: Record<string, number> = {};

  Object.entries(view.charts?.D1 ?? {}).forEach(
    ([rasi, planets]) => {
      if (!Array.isArray(planets)) return;
      const rasiIndex = rasiToIndex(rasi);
      (planets as string[]).forEach((planet) => {
        planetsByRasiIndex[planet] = rasiIndex;
      });
    }
  );

  /* ---------------- Navamsa (D9) ---------------- */

  const navamsaChart = adaptNavamsa(
    view.divisional_charts ?? view.charts
  );

  /* ---------------- All Tier-1 Divisional Charts ---------------- */
  
  const divCharts = view.divisional_charts ?? {};
  const lagnaIndex = rasiToIndex(view.lagna_details?.rasi);

  const divisionalCharts = {
    D1: {
      lagna: lagnaIndex,
      planets: planetsByRasiIndex,
    },
    D2: divCharts.D2 ? adaptDivisionalChart(divCharts.D2) : undefined,
    D7: divCharts.D7 ? adaptDivisionalChart(divCharts.D7) : undefined,
    D9: navamsaChart,
    D10: divCharts.D10 ? adaptDivisionalChart(divCharts.D10) : undefined,
  };

  /* ---------------- Final UI Model ---------------- */

  return {
    identity: {
      name: view.identity?.name ?? "Birth Chart",
      place: view.identity?.place_of_birth ?? "—",
    },

    birth: {
      date: view.birth_time?.date_of_birth ?? "—",
      time: view.birth_time?.time_of_birth ?? "—",
    },

    southIndianChart: {
      lagna: lagnaIndex,
      planets: planetsByRasiIndex,
    },

    navamsaChart,

    divisionalCharts,

    chartMetadata: view.chart_metadata ?? undefined,

    rasi: (view.rasi_view ?? []).map((r: any) => ({
      name: r.rasi,
      planets: (r.planets ?? []).map((p: any) => p.planet),
    })),

    nakshatra: (view.nakshatra_view ?? []).map((n: any) => ({
      name: n.nakshatra,
      planets: (n.planets ?? []).map((p: any) => p.planet),
    })),

    houses: (view.houses ?? []).map((h: any) => ({
      number: h.house,
      rasi: h.rasi,
      lord: h.lord,
      significations: h.significations,
      planets: h.planets ?? [],
    })),

    vimshottari: {
      timeline: view.dashas?.vimshottari?.timeline ?? [],
      current: view.dashas?.vimshottari?.current ?? null,
    },

    functional_roles: view.functional_roles ?? undefined,

    yogas: view.yogas ?? undefined,
    sade_sati: view.sade_sati ?? undefined,
    shadbala: view.shadbala ?? undefined,
  };
}

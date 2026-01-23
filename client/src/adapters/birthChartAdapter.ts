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

/**
 * Convert Navamsa structure → usable UI maps
 */
function adaptNavamsa(divisionalCharts: any) {
  const d9 = divisionalCharts?.D9 ?? {};

  const planets: Record<string, number> = {};
  const dignity: Record<
    string,
    "exalted" | "debilitated" | "neutral"
  > = {};

  Object.entries(d9).forEach(([planet, data]: any) => {
    const sign = data?.navamsa_sign;
    if (!sign) return;

    // Convert English Navamsa sign → Tamil index order
    // (UI chart still uses Tamil order)
    const tamilIndex = rasiToIndex(
      ({
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
      } as Record<string, string>)[sign]
    );

    planets[planet] = tamilIndex;
    dignity[planet] = data?.dignity ?? "neutral";
  });

  return {
    lagna: 0, // Navamsa lagna derivation is optional & future EPIC
    planets,
    dignity,
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
      lagna: rasiToIndex(view.lagna_details?.rasi),
      planets: planetsByRasiIndex,
    },

    navamsaChart,

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
  };
}

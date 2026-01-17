// client/src/adapters/birthChartAdapter.ts

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
    planets: Record<string, number>; // planet → rasi index
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
    current: string | null;
    timeline: {
      lord: string;
      start: string;
      end: string;
      partial: boolean;
    }[];
  };
}

export function adaptBirthChart(raw: any): BirthChartUIModel {
  const view = raw.view ?? raw;

  /**
   * 🔑 Build planet → rasiIndex map from charts.D1
   */
  const planetsByRasiIndex: Record<string, number> = {};

  Object.entries(view.charts?.D1 ?? {}).forEach(
    ([rasi, planets]: [string, string[]]) => {
      const rasiIndex = rasiToIndex(rasi);
      planets.forEach((planet) => {
        planetsByRasiIndex[planet] = rasiIndex;
      });
    }
  );

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
      current: view.dashas?.vimshottari?.current?.lord ?? null,
      timeline:
        view.dashas?.vimshottari?.timeline?.map((d: any) => ({
          lord: d.mahadasha,
          start: d.start,
          end: d.end,
          partial: d.is_partial,
        })) ?? [],
    },
  };
}

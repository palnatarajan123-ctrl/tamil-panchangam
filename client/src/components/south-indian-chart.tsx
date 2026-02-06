// client/src/components/south-indian-chart.tsx

interface ChartProps {
  lagna: number; // 0–11
  planets: Record<string, number>; // planet → rasi index
  dignity?: Record<string, "exalted" | "debilitated" | "neutral">;
  title?: string;     // ⬅️ IMPORTANT: passed by caller (D1 / D9 / etc)
  subtitle?: string;  // ⬅️ IMPORTANT: passed by caller
  size?: number;
  className?: string;
}

/* ============================================================
   Canonical Tamil Rāsi Names (UI Order)
   ============================================================ */

const SIGN_NAMES = [
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

/* ============================================================
   South Indian Grid Coordinates (4×4 with hollow center)
   
   STANDARD SOUTH INDIAN: Signs are FIXED in their positions.
   - [0,0] top-left = Pisces (rasi 11)
   - [1,0] = Aries (rasi 0)
   - [2,0] = Taurus (rasi 1)
   - etc. clockwise
   
   Array index corresponds to RASI INDEX (0=Aries, 11=Pisces).
   Position at HOUSE_COORDS[rasiIndex] gives the grid location.
   ============================================================ */

const HOUSE_COORDS: [number, number][] = [
  [1, 0],  // Rasi 0 (Aries) → position [1,0]
  [2, 0],  // Rasi 1 (Taurus) → position [2,0]
  [3, 0],  // Rasi 2 (Gemini) → position [3,0]
  [3, 1],  // Rasi 3 (Cancer) → position [3,1]
  [3, 2],  // Rasi 4 (Leo) → position [3,2]
  [3, 3],  // Rasi 5 (Virgo) → position [3,3]
  [2, 3],  // Rasi 6 (Libra) → position [2,3]
  [1, 3],  // Rasi 7 (Scorpio) → position [1,3]
  [0, 3],  // Rasi 8 (Sagittarius) → position [0,3]
  [0, 2],  // Rasi 9 (Capricorn) → position [0,2]
  [0, 1],  // Rasi 10 (Aquarius) → position [0,1]
  [0, 0],  // Rasi 11 (Pisces) → position [0,0] top-left
];

/* ============================================================
   Component
   ============================================================ */

export function SouthIndianChart({
  lagna,
  planets,
  dignity = {},
  title = "Rāsi Chart (D1)",      // ⬅️ default ONLY if caller forgets
  subtitle = "South Indian",
  size = 480,
  className = "",
}: ChartProps) {
  const cellSize = size / 4;
  const scaleFactor = size / 480;

  const strokeColor = "hsl(var(--border) / 0.7)";
  const textColor = "hsl(var(--foreground))";
  const mutedColor = "hsl(var(--muted-foreground))";
  const primaryColor = "hsl(var(--primary))";
  const exaltedColor = "hsl(142 72% 45%)";
  const debilitatedColor = "hsl(0 72% 55%)";

  /* ------------------------------------------------------------
     Helpers
     ------------------------------------------------------------ */

  const planetsInRasi = (rasiIndex: number): string[] =>
    Object.entries(planets)
      .filter(([_, idx]) => idx === rasiIndex)
      .map(([planet]) => planet);

  const planetColor = (planet: string) => {
    if (dignity[planet] === "exalted") return exaltedColor;
    if (dignity[planet] === "debilitated") return debilitatedColor;
    return textColor;
  };

  /* ------------------------------------------------------------
     Render
     ------------------------------------------------------------ */

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      data-testid="chart-south-indian"
    >
      {/* Outer Frame */}
      <rect
        x="0"
        y="0"
        width={size}
        height={size}
        fill="hsl(var(--card))"
        stroke={strokeColor}
        strokeWidth="1"
        rx="6"
      />

      {/* Grid */}
      {[1, 2, 3].map((i) => (
        <line
          key={`v${i}`}
          x1={cellSize * i}
          y1={0}
          x2={cellSize * i}
          y2={size}
          stroke={strokeColor}
        />
      ))}
      {[1, 2, 3].map((i) => (
        <line
          key={`h${i}`}
          x1={0}
          y1={cellSize * i}
          x2={size}
          y2={cellSize * i}
          stroke={strokeColor}
        />
      ))}

      {/* Diagonals */}
      <line
        x1={cellSize}
        y1={cellSize}
        x2={cellSize * 3}
        y2={cellSize * 3}
        stroke={strokeColor}
      />
      <line
        x1={cellSize * 3}
        y1={cellSize}
        x2={cellSize}
        y2={cellSize * 3}
        stroke={strokeColor}
      />

      {/* Houses - South Indian: Signs are FIXED, iterate by rasi index */}
      {HOUSE_COORDS.map(([col, row], rasiIndex) => {
        const signName = SIGN_NAMES[rasiIndex];
        const planetsHere = planetsInRasi(rasiIndex);
        const isLagna = rasiIndex === lagna;

        const x = col * cellSize;
        const y = row * cellSize;

        return (
          <g key={rasiIndex}>
            {/* Sign Label */}
            <text
              x={x + cellSize / 2}
              y={y + Math.round(16 * scaleFactor)}
              textAnchor="middle"
              fontSize={Math.round(13 * scaleFactor)}
              fontFamily="var(--font-mono)"
              fill={isLagna ? primaryColor : mutedColor}
              fontWeight={isLagna ? "600" : "400"}
            >
              {signName.substring(0, 3).toUpperCase()}
            </text>

            {/* Lagna marker */}
            {isLagna && (
              <text
                x={x + cellSize / 2}
                y={y + Math.round(32 * scaleFactor)}
                textAnchor="middle"
                fontSize={Math.round(12 * scaleFactor)}
                fontWeight="600"
                fill={primaryColor}
              >
                Lagna
              </text>
            )}

            {/* Planets */}
            <g transform={`translate(${x + cellSize / 2}, ${y + cellSize / 2 + Math.round(4 * scaleFactor)})`}>
              {planetsHere.map((planet, idx) => (
                <text
                  key={`${signName}-${planet}-${idx}`}
                  x={0}
                  y={idx * Math.round(16 * scaleFactor)}
                  textAnchor="middle"
                  fontSize={Math.round(14 * scaleFactor)}
                  fontWeight="500"
                  fill={planetColor(planet)}
                >
                  {planet}
                </text>
              ))}
            </g>
          </g>
        );
      })}

      {/* Center Panel */}
      <rect
        x={cellSize}
        y={cellSize}
        width={cellSize * 2}
        height={cellSize * 2}
        fill="hsl(var(--background) / 0.55)"
        rx="4"
      />

      {/* CENTER LABEL */}
      <text
        x={size / 2}
        y={size / 2 - Math.round(8 * scaleFactor)}
        textAnchor="middle"
        fontSize={Math.round(16 * scaleFactor)}
        fontWeight="700"
        fill="hsl(var(--foreground))"
      >
        {title}
      </text>

      <text
        x={size / 2}
        y={size / 2 + Math.round(14 * scaleFactor)}
        textAnchor="middle"
        fontSize={Math.round(12 * scaleFactor)}
        fill="hsl(var(--muted-foreground))"
      >
        {subtitle}
      </text>
    </svg>
  );
}

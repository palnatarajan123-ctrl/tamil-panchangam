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
   ============================================================ */

const HOUSE_COORDS: [number, number][] = [
  [1, 0],
  [2, 0],
  [3, 0],
  [3, 1],
  [3, 2],
  [3, 3],
  [2, 3],
  [1, 3],
  [0, 3],
  [0, 2],
  [0, 1],
  [0, 0],
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
  size = 360,
  className = "",
}: ChartProps) {
  const cellSize = size / 4;

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

      {/* Houses */}
      {HOUSE_COORDS.map(([col, row], index) => {
        const rasiIndex = (index + lagna) % 12;
        const signName = SIGN_NAMES[rasiIndex];
        const planetsHere = planetsInRasi(rasiIndex);
        const isLagna = rasiIndex === lagna;

        const x = col * cellSize;
        const y = row * cellSize;

        return (
          <g key={index}>
            {/* Sign Label */}
            <text
              x={x + cellSize / 2}
              y={y + 12}
              textAnchor="middle"
              fontSize="9"
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
                y={y + 24}
                textAnchor="middle"
                fontSize="9"
                fontWeight="600"
                fill={primaryColor}
              >
                Lagna
              </text>
            )}

            {/* Planets */}
            <g transform={`translate(${x + cellSize / 2}, ${y + cellSize / 2 + 6})`}>
              {planetsHere.map((planet, idx) => (
                <text
                  key={`${signName}-${planet}-${idx}`}
                  x={0}
                  y={idx * 12}
                  textAnchor="middle"
                  fontSize="11"
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

      {/* ✅ CENTER LABEL — caller-controlled */}
      <text
        x={size / 2}
        y={size / 2 - 6}
        textAnchor="middle"
        fontSize="13"
        fontWeight="700"
        fill="hsl(var(--foreground))"
      >
        {title}
      </text>

      <text
        x={size / 2}
        y={size / 2 + 12}
        textAnchor="middle"
        fontSize="10"
        fill="hsl(var(--muted-foreground))"
      >
        {subtitle}
      </text>
    </svg>
  );
}

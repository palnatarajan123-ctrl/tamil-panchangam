// client/src/components/south-indian-chart.tsx

interface ChartProps {
  lagna: number;                         // 0–11 (MANDATORY)
  planets: Record<string, number>;       // planet → rasi index
  size?: number;
  className?: string;
}

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

// Planet abbreviations
const PLANET_ABBR: Record<string, string> = {
  Sun: "Su",
  Moon: "Mo",
  Mars: "Ma",
  Mercury: "Me",
  Jupiter: "Ju",
  Venus: "Ve",
  Saturn: "Sa",
  Rahu: "Ra",
  Ketu: "Ke",
};

export function SouthIndianChart({
  lagna,
  planets,
  size = 320,
  className = "",
}: ChartProps) {
  const cellSize = size / 4;

  const strokeColor = "hsl(var(--border) / 0.7)";
  const textColor = "hsl(var(--foreground))";
  const mutedColor = "hsl(var(--muted-foreground))";
  const primaryColor = "hsl(var(--primary))";

  /**
   * 🔑 Canonical lookup:
   * For a given rasi index, return all planets in it
   */
  const planetsInRasi = (rasiIndex: number): string[] =>
    Object.entries(planets)
      .filter(([_, idx]) => idx === rasiIndex)
      .map(([planet]) => PLANET_ABBR[planet] ?? planet);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      data-testid="chart-south-indian"
    >
      {/* Outer frame */}
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
          y1="0"
          x2={cellSize * i}
          y2={size}
          stroke={strokeColor}
        />
      ))}
      {[1, 2, 3].map((i) => (
        <line
          key={`h${i}`}
          x1="0"
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

        const x = col * cellSize;
        const y = row * cellSize;
        const isLagna = rasiIndex === lagna;

        return (
          <g key={index}>
            {/* Sign label */}
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

            {/* Lagna */}
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
                  fill={textColor}
                >
                  {planet}
                </text>
              ))}
            </g>
          </g>
        );
      })}

      {/* Center */}
      <rect
        x={cellSize}
        y={cellSize}
        width={cellSize * 2}
        height={cellSize * 2}
        fill="hsl(var(--muted) / 0.25)"
      />
      <text
        x={size / 2}
        y={size / 2 - 8}
        textAnchor="middle"
        fontSize="12"
        fontWeight="600"
      >
        D1 Rāsi
      </text>
      <text
        x={size / 2}
        y={size / 2 + 10}
        textAnchor="middle"
        fontSize="9"
        fill={mutedColor}
      >
        South Indian
      </text>
    </svg>
  );
}

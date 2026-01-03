interface ChartProps {
  lagna?: number;
  planets?: Record<string, number>;
  size?: number;
  className?: string;
}

const SIGN_NAMES = [
  "Mesha", "Vrishabha", "Mithuna", "Kataka",
  "Simha", "Kanya", "Tula", "Vrischika",
  "Dhanus", "Makara", "Kumbha", "Meena"
];

const HOUSE_COORDS: [number, number][] = [
  [1, 0], [2, 0], [3, 0], [3, 1],
  [3, 2], [3, 3], [2, 3], [1, 3],
  [0, 3], [0, 2], [0, 1], [0, 0]
];

export function SouthIndianChart({ lagna = 0, planets = {}, size = 320, className = "" }: ChartProps) {
  const cellSize = size / 4;
  const strokeColor = "hsl(var(--border))";
  const textColor = "hsl(var(--foreground))";
  const mutedColor = "hsl(var(--muted-foreground))";
  const primaryColor = "hsl(var(--primary))";

  const getPlanetsInHouse = (house: number): string[] => {
    return Object.entries(planets)
      .filter(([_, h]) => h === house)
      .map(([planet]) => planet);
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      data-testid="chart-south-indian"
    >
      <rect
        x="0"
        y="0"
        width={size}
        height={size}
        fill="hsl(var(--card))"
        stroke={strokeColor}
        strokeWidth="1"
        rx="4"
      />

      {[1, 2, 3].map((i) => (
        <line
          key={`v${i}`}
          x1={cellSize * i}
          y1="0"
          x2={cellSize * i}
          y2={size}
          stroke={strokeColor}
          strokeWidth="1"
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
          strokeWidth="1"
        />
      ))}

      <line x1={cellSize} y1={cellSize} x2={cellSize * 3} y2={cellSize * 3} stroke={strokeColor} strokeWidth="1" />
      <line x1={cellSize * 3} y1={cellSize} x2={cellSize} y2={cellSize * 3} stroke={strokeColor} strokeWidth="1" />

      {HOUSE_COORDS.map(([col, row], index) => {
        const house = (index + lagna) % 12;
        const signName = SIGN_NAMES[house];
        const planetsHere = getPlanetsInHouse(house);
        const x = col * cellSize;
        const y = row * cellSize;
        const isLagna = house === lagna;

        return (
          <g key={index}>
            <text
              x={x + cellSize / 2}
              y={y + 14}
              textAnchor="middle"
              fontSize="9"
              fontFamily="var(--font-mono)"
              fill={isLagna ? primaryColor : mutedColor}
              fontWeight={isLagna ? "600" : "400"}
            >
              {signName.substring(0, 3).toUpperCase()}
            </text>

            {planetsHere.map((planet, idx) => (
              <text
                key={planet}
                x={x + cellSize / 2}
                y={y + 30 + idx * 14}
                textAnchor="middle"
                fontSize="11"
                fontFamily="var(--font-sans)"
                fontWeight="500"
                fill={textColor}
              >
                {planet}
              </text>
            ))}

            {isLagna && (
              <text
                x={x + 8}
                y={y + cellSize - 8}
                fontSize="10"
                fontFamily="var(--font-serif)"
                fontWeight="600"
                fill={primaryColor}
              >
                Asc
              </text>
            )}
          </g>
        );
      })}

      <rect
        x={cellSize}
        y={cellSize}
        width={cellSize * 2}
        height={cellSize * 2}
        fill="hsl(var(--muted) / 0.3)"
        stroke="none"
      />
      <text
        x={size / 2}
        y={size / 2 - 10}
        textAnchor="middle"
        fontSize="12"
        fontFamily="var(--font-serif)"
        fontWeight="600"
        fill={textColor}
      >
        D1 Rasi
      </text>
      <text
        x={size / 2}
        y={size / 2 + 10}
        textAnchor="middle"
        fontSize="9"
        fontFamily="var(--font-sans)"
        fill={mutedColor}
      >
        South Indian
      </text>
    </svg>
  );
}

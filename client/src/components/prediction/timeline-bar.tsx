type Segment = {
  start: string;
  end: string;
  strength: number;
  tags: string[];
};

export function TimelineBar({ timeline }: { timeline: Segment[] }) {
  if (!timeline.length) return null;

  return (
    <div className="rounded-lg border p-4">
      <div className="font-medium mb-2">Timeline</div>

      <div className="flex h-6 w-full overflow-hidden rounded">
        {timeline.map((seg, i) => (
          <div
            key={i}
            title={`${seg.start} → ${seg.end}`}
            style={{
              width: `${100 / timeline.length}%`,
              backgroundColor: strengthColor(seg.strength),
            }}
          />
        ))}
      </div>
    </div>
  );
}

function strengthColor(v: number) {
  if (v >= 0.75) return "#16a34a"; // strong
  if (v >= 0.55) return "#eab308"; // medium
  return "#dc2626";               // weak
}

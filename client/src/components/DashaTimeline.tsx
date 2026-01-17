interface Dasha {
  mahadasha: string;
  start: string;
  end: string;
  is_partial: boolean;
}

export function DashaTimeline({
  timeline,
  current
}: {
  timeline?: Dasha[] | null;
  current: any;
}) {
  // 🔒 Hard guard — prevents blank screen
  if (!timeline || timeline.length === 0) {
    return (
      <div className="space-y-2">
        <h4 className="font-semibold">Vimshottari Dasha</h4>

        <div className="p-4 rounded-lg bg-gray-50 border text-sm text-gray-600">
          <div className="font-medium mb-1">
            Current Mahadasha: {current?.lord ?? "—"}
          </div>
          <div>
            {current?.start?.slice(0, 10)} –{" "}
            {current?.end?.slice(0, 10)}
          </div>
          {current?.is_partial && (
            <div className="text-xs text-amber-600 mt-1">
              Partial dasha period
            </div>
          )}
        </div>
      </div>
    );
  }

  // ✅ Full timeline rendering (future-ready)
  return (
    <div className="space-y-2">
      <h4 className="font-semibold">Vimshottari Dasha Timeline</h4>

      <div className="flex overflow-x-auto gap-2">
        {timeline.map((dasha, i) => {
          const isActive = dasha.mahadasha === current?.lord;

          return (
            <div
              key={i}
              className={`min-w-[120px] p-3 rounded-lg border text-center ${
                isActive
                  ? "bg-indigo-100 border-indigo-400"
                  : "bg-gray-50"
              }`}
            >
              <div className="font-medium">{dasha.mahadasha}</div>
              <div className="text-xs text-gray-500">
                {dasha.start.slice(0, 4)} – {dasha.end.slice(0, 4)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

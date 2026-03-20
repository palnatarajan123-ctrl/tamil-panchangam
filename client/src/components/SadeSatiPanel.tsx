import { ShieldAlert, ShieldCheck, AlertCircle, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BirthChartUIModel } from "@/adapters/birthChartAdapter";

type SadeSatiData = NonNullable<BirthChartUIModel["sade_sati"]>;

// ─── Helpers ───────────────────────────────────────────────────────────────

function formatDate(d: string | null | undefined): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-IN", {
      month: "short",
      year: "numeric",
    });
  } catch {
    return d;
  }
}

function AlertBox({
  color,
  title,
  children,
}: {
  color: "red" | "amber" | "orange" | "green";
  title: string;
  children: React.ReactNode;
}) {
  const map = {
    red: "border-red-500/30 bg-red-500/10 text-red-400",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    orange: "border-orange-500/30 bg-orange-500/10 text-orange-400",
    green: "border-green-500/30 bg-green-500/10 text-green-400",
  };
  return (
    <div className={`rounded-lg border p-4 ${map[color]}`}>
      <p className="font-semibold text-sm mb-2">{title}</p>
      {children}
    </div>
  );
}

function EffectsList({ effects }: { effects: string[] }) {
  if (!effects.length) return null;
  return (
    <ul className="space-y-1 mt-2">
      {effects.map((e, i) => (
        <li key={i} className="text-xs flex gap-1.5">
          <span className="mt-0.5 shrink-0">•</span>
          <span className="text-current/80">{e}</span>
        </li>
      ))}
    </ul>
  );
}

function RemediesList({ remedies }: { remedies: string[] }) {
  if (!remedies.length) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold mb-1 opacity-80">Suggested Remedies:</p>
      <ul className="space-y-1">
        {remedies.map((r, i) => (
          <li key={i} className="text-xs flex gap-1.5">
            <span className="mt-0.5 shrink-0">→</span>
            <span className="text-current/80">{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Windows Table ─────────────────────────────────────────────────────────

function WindowsTable({
  windows,
}: {
  windows: SadeSatiData["sade_sati"]["all_windows"];
}) {
  if (!windows.length) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        Saturn Phase Windows
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-1.5 pr-4 text-muted-foreground font-medium">Phase</th>
              <th className="text-left py-1.5 pr-4 text-muted-foreground font-medium">Saturn Sign</th>
              <th className="text-left py-1.5 text-muted-foreground font-medium">Period</th>
            </tr>
          </thead>
          <tbody>
            {windows.map((w, i) => {
              const phaseLabel =
                w.phase === -1
                  ? "Rising (12th)"
                  : w.phase === 0
                  ? "Peak (Moon sign)"
                  : "Setting (2nd)";
              return (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-1.5 pr-4">{phaseLabel}</td>
                  <td className="py-1.5 pr-4 text-muted-foreground">{w.saturn_sign_name}</td>
                  <td className="py-1.5 text-muted-foreground">
                    {formatDate(w.start_date)} – {formatDate(w.end_date)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Panel ─────────────────────────────────────────────────────────────────

export function SadeSatiPanel({ sadeSati }: { sadeSati: BirthChartUIModel["sade_sati"] }) {
  if (!sadeSati) return null;

  const ss = sadeSati.sade_sati;
  const ashtama = sadeSati.ashtama_shani;
  const kantaka = sadeSati.kantaka_shani;
  const alertLevel = sadeSati.alert_level;

  return (
    <Card className="border-muted">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {alertLevel === "low" ? (
            <ShieldCheck className="h-4 w-4 text-green-500" />
          ) : alertLevel === "high" ? (
            <ShieldAlert className="h-4 w-4 text-red-500" />
          ) : (
            <AlertCircle className="h-4 w-4 text-amber-500" />
          )}
          Sade Sati &amp; Saturn Phases
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Moon sign context */}
        <p className="text-sm text-muted-foreground">
          Natal Moon in{" "}
          <span className="font-medium text-foreground">{sadeSati.moon_sign_name}</span>
          {" · "}Saturn currently in{" "}
          <span className="font-medium text-foreground">
            {sadeSati.current_saturn_sign_name ?? "—"}
          </span>
          {sadeSati.saturn_house_from_moon != null && (
            <> (H{sadeSati.saturn_house_from_moon} from Moon)</>
          )}
        </p>

        {/* Low alert — no challenge */}
        {alertLevel === "low" && !ss.active && !ashtama.active && !kantaka.active && (
          <AlertBox color="green" title="Saturn is not in a challenging position from your Moon">
            <p className="text-xs text-current/80">{ss.summary}</p>
          </AlertBox>
        )}

        {/* Sade Sati active */}
        {ss.active && ss.phase != null && (
          <AlertBox
            color={ss.phase === 0 ? "red" : "amber"}
            title={`Sade Sati Active — ${ss.phase_name ?? ""}`}
          >
            <div className="flex items-center gap-1.5 text-xs mb-2">
              <Clock className="h-3.5 w-3.5" />
              <span>
                Current phase ends:{" "}
                <span className="font-medium">{formatDate(ss.current_phase_ends)}</span>
              </span>
            </div>
            <EffectsList effects={ss.effects} />
            <RemediesList remedies={ss.remedies} />
          </AlertBox>
        )}

        {/* Ashtama Shani */}
        {ashtama.active && (
          <AlertBox color="orange" title="Ashtama Shani Active — Saturn in 8th from Moon">
            <div className="flex items-center gap-1.5 text-xs mb-2">
              <Clock className="h-3.5 w-3.5" />
              <span>
                Ends: <span className="font-medium">{formatDate(ashtama.ends)}</span>
              </span>
            </div>
            <EffectsList effects={ashtama.effects} />
            <RemediesList remedies={ashtama.remedies} />
          </AlertBox>
        )}

        {/* Kantaka Shani */}
        {kantaka.active && (
          <AlertBox color="amber" title="Kantaka Shani — Saturn in 4th from Moon">
            <div className="flex items-center gap-1.5 text-xs mb-2">
              <Clock className="h-3.5 w-3.5" />
              <span>
                Ends: <span className="font-medium">{formatDate(kantaka.ends)}</span>
              </span>
            </div>
            <EffectsList effects={kantaka.effects} />
          </AlertBox>
        )}

        {/* Windows table — always show */}
        <WindowsTable windows={ss.all_windows} />
      </CardContent>
    </Card>
  );
}

/**
 * LabValueCard — single lab value with value, unit, reference range, sparkline,
 * provenance badge.
 *
 * Per docs/patient-app-design.md §4.2. Phase 2a wires it to real data from the
 * /labs/results/ endpoint via a test abbreviation.
 */
import { useMemo, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUp, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { DataSourceBadge } from "@/components/healthkey/DataSourceBadge";
import { Card, CardContent } from "@/components/ui/card";
import { useLabResults } from "@/features/labs/api";
import type { LabResult } from "@/types/labs";

interface Props {
  testAbbrev: string;
  title?: string;
}

export function LabValueCard({ testAbbrev, title }: Props) {
  const { data: results = [], isLoading } = useLabResults({ test: testAbbrev });

  if (isLoading) return <CardSkeleton />;
  if (results.length === 0) return null;

  // Results come sorted newest first from the API
  const latest = results[0];
  const previous = results[1];

  return (
    <Link
      to={`/dashboard/records/labs/${testAbbrev}`}
      className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700 focus-visible:ring-offset-2"
      aria-label={`Open ${title ?? latest.test.name} trend`}
    >
      <Card className="transition-colors hover:bg-muted/30">
        <CardContent className="p-5">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="min-w-0 truncate text-base font-semibold text-foreground">
            {title ?? latest.test.name}
          </h3>
          <div className="flex shrink-0 items-center gap-1.5">
            <TrendBadge latest={latest} previous={previous} />
            <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          </div>
        </div>

        {/* Two-column row:
            - Left:  value on top, Normal range caption stacked below
            - Right: sparkline, taller (h-12) so it spans both text lines
                     vertically. items-center on the row vertically aligns
                     the sparkline with the stacked text.
        */}
        <div className="flex items-center gap-4">
          <div className="min-w-0">
            <div className="font-mono text-2xl font-semibold text-foreground">
              {formatValue(latest)}
              {latest.unit && (
                <span className="ml-1 text-sm font-normal text-muted-foreground">
                  {latest.unit}
                </span>
              )}
            </div>
            {latest.reference_min != null && latest.reference_max != null ? (
              <p className="mt-0.5 whitespace-nowrap text-xs text-muted-foreground">
                Normal: {latest.reference_min}–{latest.reference_max} {latest.unit}
              </p>
            ) : (
              // Placeholder so all cards have the same height regardless of
              // whether the test has a default reference range. Italic so it
              // reads as "field intentionally empty", not as a real range.
              <p className="mt-0.5 whitespace-nowrap text-xs italic text-muted-foreground/70">
                No range
              </p>
            )}
          </div>

          {results.length > 1 && (
            <div className="ml-auto h-12 w-24 shrink-0 sm:w-32">
              <Sparkline results={results.slice(0, 6).reverse()} unit={latest.unit} />
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center gap-2 text-xs">
          <StatusChip status={latest.status} />
          <DataSourceBadge
            source={latest.source === "manual" ? "manual" : "document"}
            detail={latest.source === "manual" ? "You" : undefined}
            timeAgo={formatTimeAgo(latest.measured_at ?? latest.created_at)}
          />
        </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function formatValue(r: LabResult): string {
  if (r.value != null) {
    // Keep 1-2 decimals for readability; drop trailing zeros
    return String(Number(r.value.toFixed(2)));
  }
  return r.value_qualitative || "—";
}

/**
 * TrendBadge — coloured pill showing how the latest value changed vs the
 * previous measurement.
 *
 * Semantics (this is the non-obvious bit):
 *   The colour is NOT based on arrow direction. An "up" arrow isn't always
 *   good (LDL cholesterol going up is bad; hemoglobin recovering from anemia
 *   going up is good). The colour reflects whether the value moved CLOSER TO
 *   or AWAY FROM the test's reference range:
 *
 *     improving (green):  distance from range decreased (or stayed 0 and we
 *                         had a real delta within range)
 *     worsening (amber):  distance from range increased
 *     stable    (gray):   no reference range available, or both readings in
 *                         range with minimal change
 *
 * The arrow still shows raw delta direction so the user can see which way
 * the number moved; the colour tells them whether that was good or bad.
 *
 * Renders nothing when there's no previous reading to compare against, or
 * when either value is null (qualitative results).
 */
function TrendBadge({
  latest,
  previous,
}: {
  latest: LabResult;
  previous?: LabResult;
}) {
  if (!previous || latest.value == null || previous.value == null) return null;

  const delta = latest.value - previous.value;
  const pctChange = Math.abs(delta) / (Math.abs(previous.value) || 1);
  const direction: "up" | "down" | "flat" =
    pctChange < 0.02 ? "flat" : delta > 0 ? "up" : "down";

  // Tone from distance-to-range: improving / worsening / stable
  let tone: "improving" | "worsening" | "stable" = "stable";
  if (latest.reference_min != null && latest.reference_max != null) {
    const distanceFromRange = (v: number) => {
      if (v < latest.reference_min!) return latest.reference_min! - v;
      if (v > latest.reference_max!) return v - latest.reference_max!;
      return 0;
    };
    const distNow = distanceFromRange(latest.value);
    const distPrev = distanceFromRange(previous.value);
    const EPS = 1e-4;
    if (distNow < distPrev - EPS) tone = "improving";
    else if (distNow > distPrev + EPS) tone = "worsening";
  }

  const styles: Record<typeof tone, string> = {
    improving: "bg-success-50 text-success-700 border-success-200",
    worsening: "bg-warning-50 text-warning-700 border-warning-200",
    stable: "bg-muted text-muted-foreground border-border",
  };

  const Icon =
    direction === "up" ? ArrowUp : direction === "down" ? ArrowDown : ArrowRight;

  // Format the delta: "+0.7", "−1.2", "±0" (use a proper minus sign for
  // the negative case so it sits visually with the plus sign).
  const absRounded =
    Math.abs(delta) >= 10
      ? Math.round(Math.abs(delta)).toString()
      : (Math.round(Math.abs(delta) * 10) / 10).toString();
  const formattedDelta =
    direction === "flat" ? "±0" : `${delta > 0 ? "+" : "−"}${absRounded}`;

  const toneLabel =
    tone === "improving"
      ? "Moved toward normal range"
      : tone === "worsening"
        ? "Moved away from normal range"
        : latest.reference_min == null
          ? "Change from previous reading"
          : "Still within normal range";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${styles[tone]}`}
      title={`${formattedDelta} ${latest.unit} — ${toneLabel}`}
      aria-label={`Trend: ${tone}, ${formattedDelta} ${latest.unit}`}
    >
      <Icon className="h-3 w-3" strokeWidth={2.5} aria-hidden="true" />
      <span className="font-mono">{formattedDelta}</span>
    </span>
  );
}

function StatusChip({ status }: { status: LabResult["status"] }) {
  // "unknown" means the test has no reference range, so "in / below / above"
  // isn't meaningful. The italic "No range" placeholder in the range line
  // already communicates that — don't double-label it here.
  if (status === "unknown") return null;

  const styles: Record<Exclude<LabResult["status"], "unknown">, string> = {
    in_range: "bg-success-50 text-success-700 border-success-200",
    below: "bg-warning-50 text-warning-700 border-warning-200",
    above: "bg-warning-50 text-warning-700 border-warning-200",
  };
  const labels: Record<Exclude<LabResult["status"], "unknown">, string> = {
    in_range: "Normal",
    below: "Below",
    above: "Above",
  };
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

/**
 * Inline sparkline of the last N values — shape indicator, not a precision plot.
 *
 * Approach:
 *  - The polyline lives inside an SVG with preserveAspectRatio="none" so the
 *    trend stretches horizontally to fill the card width. (A line is still a
 *    line after non-uniform scaling; only the slope changes, which is fine
 *    for a shape indicator.)
 *  - The data points are rendered as **HTML divs** absolutely positioned over
 *    the SVG. CSS circles stay perfectly round regardless of container aspect
 *    ratio — a <circle> inside a non-uniformly scaled SVG would render as an
 *    ellipse, which was the bug.
 *  - Hover (mouse only — touch taps fall through to the parent Link) reveals a
 *    small value/date tooltip above the hovered point. Position is a percentage
 *    so it tracks the dot as the sparkline stretches.
 */
function Sparkline({ results, unit }: { results: LabResult[]; unit: string }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  type NumericPoint = LabResult & { value: number };
  const dataPoints = useMemo(
    () => results.filter((r): r is NumericPoint => typeof r.value === "number"),
    [results],
  );
  if (dataPoints.length < 2) return null;

  const values = dataPoints.map((r) => r.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;

  // Shared coordinate system (0-100 in both axes) for both the SVG polyline
  // and the HTML dot positions. The inset keeps dots off the wrapper edges
  // so a 7px circle centered with translate(-50%,-50%) stays fully inside.
  const X_INSET = 4; // %
  const Y_INSET = 18; // %

  const points = dataPoints.map((r, i) => {
    const xPct =
      X_INSET + (i / (dataPoints.length - 1)) * (100 - 2 * X_INSET);
    // Y=0 is top in both SVG and CSS, so higher values → lower yPct
    const yPct =
      Y_INSET + (1 - (r.value - minV) / range) * (100 - 2 * Y_INSET);
    return { xPct, yPct };
  });
  const polylinePoints = points
    .map((p) => `${p.xPct.toFixed(2)},${p.yPct.toFixed(2)}`)
    .join(" ");

  const hoveredPoint = hoveredIdx != null ? dataPoints[hoveredIdx] : null;
  const hoveredXPct = hoveredIdx != null ? points[hoveredIdx].xPct : 0;

  return (
    <div
      // Fills the parent's box. The parent is responsible for setting
      // a fixed height (e.g. h-12) so the SVG has a known viewport.
      className="relative h-full w-full"
      onPointerLeave={() => setHoveredIdx(null)}
    >
      {/* Stretched SVG for the polyline only — the line renders correctly
          under non-uniform scaling; only circles would have distorted. */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="absolute inset-0 block h-full w-full overflow-visible text-healthkey-brand-700"
        role="img"
        aria-label={`Recent ${unit} trend`}
      >
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          vectorEffect="non-scaling-stroke"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* HTML dots — CSS circles stay perfectly round regardless of the
          wrapper's aspect ratio. */}
      {points.map((p, i) => {
        const point = dataPoints[i];
        const titleDate = point.measured_at
          ? ` · ${formatShortDate(point.measured_at)}`
          : "";
        return (
          <div
            key={i}
            className="absolute h-[7px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full border-[1.5px] border-[hsl(var(--background))] bg-healthkey-brand-700"
            style={{ left: `${p.xPct}%`, top: `${p.yPct}%` }}
            title={`${formatValue(point)} ${unit}${titleDate}`}
            onPointerEnter={(e) => {
              if (e.pointerType === "mouse") setHoveredIdx(i);
            }}
            onPointerLeave={(e) => {
              if (e.pointerType === "mouse") setHoveredIdx(null);
            }}
          />
        );
      })}

      {hoveredPoint && (
        <div
          className="pointer-events-none absolute -top-10 z-10 whitespace-nowrap rounded-md border border-border bg-card px-2 py-1 text-[11px] shadow-md"
          style={{
            left: `${hoveredXPct}%`,
            transform: "translateX(-50%)",
          }}
          role="tooltip"
        >
          <div className="font-mono font-semibold text-foreground">
            {formatValue(hoveredPoint)}{" "}
            <span className="text-muted-foreground">{unit}</span>
          </div>
          {hoveredPoint.measured_at && (
            <div className="text-muted-foreground">
              {formatShortDate(hoveredPoint.measured_at)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function CardSkeleton() {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="h-4 w-24 animate-pulse rounded bg-muted" />
        <div className="mt-3 h-8 w-16 animate-pulse rounded bg-muted" />
        <div className="mt-2 h-3 w-32 animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}

function formatTimeAgo(iso: string | null): string | undefined {
  if (!iso) return undefined;
  const then = new Date(iso);
  const now = new Date();
  const days = Math.floor((now.getTime() - then.getTime()) / (1000 * 60 * 60 * 24));
  if (days < 1) return "today";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return then.toISOString().slice(0, 10);
}

/**
 * LabValueCard — single lab value with value, unit, reference range, sparkline,
 * provenance badge.
 *
 * Per docs/patient-app-design.md §4.2. Phase 2a wires it to real data from the
 * /labs/results/ endpoint via a test abbreviation.
 */
import { useMemo } from "react";
import { ArrowDown, ArrowRight, ArrowUp, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";

import { DataSourceBadge } from "@/components/healthkey/DataSourceBadge";
import type { AxiosInstance } from "axios";
import { FileSourceBadge } from "@/components/labs/FileSourceBadge";
import { Card, CardContent } from "@/components/ui/card";
import { useLabResults } from "@/features/labs/api";
import type { LabValue } from "@/types/labs";

interface Props {
  testAbbrev: string;
  title?: string;
  onNavigate?: (testAbbreviation: string) => void;
  apiClient?: AxiosInstance;
}

export function LabValueCard({ testAbbrev, title, onNavigate, apiClient }: Props) {
  const { data: results = [], isLoading } = useLabResults({ test: testAbbrev }, apiClient);

  if (isLoading) return <CardSkeleton />;
  if (results.length === 0) return null;

  // Results come sorted newest first from the API
  const latest = results[0];
  const previous = results[1];

  const cardContent = (
    <Card className="transition-colors hover:bg-muted/30">
      <CardContent className="p-5">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-healthkey-text-secondary">
              {title ?? latest.test.name}
            </h3>
            {latest.test.loinc_name && latest.test.loinc_name !== latest.test.name && (
              <p className="truncate text-xs text-muted-foreground">
                {latest.test.loinc_name}
              </p>
            )}
          </div>
          <div className="mt-0.5 flex shrink-0 items-center gap-1.5">
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
            <div className="font-mono text-xl font-semibold text-healthkey-text-secondary">
              {formatValue(latest)}
              {latest.unit && (
                <span className="ml-1 text-sm font-normal text-muted-foreground">
                  {latest.unit}
                </span>
              )}
            </div>
            {latest.reference_min != null || latest.reference_max != null ? (
              <p className="mt-0.5 whitespace-nowrap text-xs text-muted-foreground">
                Normal: {formatRange(latest.reference_min, latest.reference_max, latest.unit)}
              </p>
            ) : (
              <p className="mt-0.5 whitespace-nowrap text-xs italic text-muted-foreground/70">
                No range
              </p>
            )}
            <ReferenceTextNote text={latest.reference_text} />
          </div>

          {results.length > 1 && (
            <div className="ml-auto h-12 w-24 shrink-0 sm:w-32">
              <Sparkline results={results.slice(0, 6).reverse()} unit={latest.unit} />
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center gap-2 text-xs">
          <StatusChip status={latest.status} />
          {latest.source !== "manual" && latest.source_filename ? (
            <div className="min-w-0 flex-1">
              <FileSourceBadge
                filename={latest.source_filename}
                timeAgo={formatTimeAgo(latest.measured_at ?? latest.created_at)}
                fullWidth
              />
            </div>
          ) : (
            <DataSourceBadge
              source={latest.source === "manual" ? "manual" : "document"}
              detail={latest.source === "manual" ? "You" : undefined}
              timeAgo={formatTimeAgo(latest.measured_at ?? latest.created_at)}
            />
          )}
        </div>
        </CardContent>
      </Card>
  );

  if (onNavigate) {
    return (
      <button
        type="button"
        onClick={() => onNavigate(testAbbrev)}
        className="block w-full cursor-pointer rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700 focus-visible:ring-offset-2"
        aria-label={`Open ${title ?? latest.test.name} trend`}
      >
        {cardContent}
      </button>
    );
  }

  return (
    <Link
      to={`/dashboard/records/labs/${testAbbrev}`}
      className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700 focus-visible:ring-offset-2"
      aria-label={`Open ${title ?? latest.test.name} trend`}
    >
      {cardContent}
    </Link>
  );
}

function ReferenceTextNote({ text }: { text?: string }) {
  if (!text) return null;
  const lines = text.split("\n");
  if (lines.length <= 1) return null;
  const extra = lines.slice(1).filter((l) => l.trim());
  if (extra.length === 0) return null;
  return (
    <div className="mt-0.5 space-y-px text-[11px] leading-tight text-muted-foreground/80">
      {extra.map((line, i) => (
        <p key={i}>{line}</p>
      ))}
    </div>
  );
}

function fmtNum(n: number): string {
  return String(Number(n.toFixed(2)));
}

function formatRange(min: number | null, max: number | null, unit: string): string {
  if (min != null && max != null) return `${fmtNum(min)}–${fmtNum(max)} ${unit}`;
  if (max != null) return `< ${fmtNum(max)} ${unit}`;
  if (min != null) return `> ${fmtNum(min)} ${unit}`;
  return "";
}

function formatValue(r: LabValue): string {
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
  latest: LabValue;
  previous?: LabValue;
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

function StatusChip({ status }: { status: LabValue["status"] }) {
  // "unknown" means the test has no reference range, so "in / below / above"
  // isn't meaningful. The italic "No range" placeholder in the range line
  // already communicates that — don't double-label it here.
  if (status === "unknown") return null;

  const styles: Record<Exclude<LabValue["status"], "unknown">, string> = {
    in_range: "bg-success-50 text-success-700 border-success-200",
    below: "bg-warning-50 text-warning-700 border-warning-200",
    above: "bg-warning-50 text-warning-700 border-warning-200",
  };
  const labels: Record<Exclude<LabValue["status"], "unknown">, string> = {
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
 * Uses recharts' LineChart with a monotone curve so the line is smooth instead
 * of a straight polyline between points. The tooltip uses
 * `allowEscapeViewBox` so it can render above the tiny h-12 container without
 * being clipped.
 */
type SparkPoint = { value: number; measured_at: string | null };

function Sparkline({ results, unit }: { results: LabValue[]; unit: string }) {
  const chartData = useMemo<SparkPoint[]>(
    () =>
      results
        .filter((r): r is LabValue & { value: number } => typeof r.value === "number")
        .map((r) => ({ value: r.value, measured_at: r.measured_at })),
    [results],
  );
  if (chartData.length < 2) return null;

  return (
    <div
      className="h-full w-full text-healthkey-brand-700"
      role="img"
      aria-label={`Recent ${unit} trend`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 6, right: 6, bottom: 6, left: 6 }}>
          <Tooltip
            cursor={false}
            allowEscapeViewBox={{ x: true, y: true }}
            wrapperStyle={{ outline: "none", zIndex: 10 }}
            content={<SparkTooltip unit={unit} />}
          />
          <Line
            type="natural"
            dataKey="value"
            stroke="currentColor"
            strokeWidth={1.75}
            strokeLinecap="round"
            strokeLinejoin="round"
            isAnimationActive={false}
            dot={{
              r: 2.5,
              fill: "currentColor",
              stroke: "hsl(var(--background))",
              strokeWidth: 1.5,
            }}
            activeDot={{
              r: 3.5,
              fill: "currentColor",
              stroke: "hsl(var(--background))",
              strokeWidth: 1.5,
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SparkTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ payload: SparkPoint }>;
  unit: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const { value, measured_at } = payload[0].payload;
  return (
    <div className="pointer-events-none whitespace-nowrap rounded-md border border-border bg-card px-2 py-1 text-[11px] shadow-md">
      <div className="font-mono font-semibold text-foreground">
        {String(Number(value.toFixed(2)))}{" "}
        <span className="text-muted-foreground">{unit}</span>
      </div>
      {measured_at && (
        <div className="text-muted-foreground">{formatShortDate(measured_at)}</div>
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

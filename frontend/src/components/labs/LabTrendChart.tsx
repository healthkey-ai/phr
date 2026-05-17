/**
 * LabTrendChart — full time-series view of a single lab over time.
 * Per docs/patient-app-design.md §4.2 + §5.8.
 *
 * - Area chart with gradient fill under the curve (clipped by the curve)
 * - Reference range shown as horizontal dashed lines at min/max
 * - Out-of-range points highlighted via status colour
 * - Empty state: < 1 data point → "Not enough data for a trend yet"
 * - Partial state: exactly 1 data point → render a single dot
 */
import {
  Area,
  AreaChart,
  CartesianGrid,
  Dot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { AxiosInstance } from "axios";
import { useLabResults } from "@/features/labs/api";
import type { LabValue } from "@/types/labs";

interface Props {
  testAbbrev: string;
  apiClient?: AxiosInstance;
}

interface ChartPoint {
  date: string;           // YYYY-MM-DD
  label: string;          // "Mar 15"
  value: number;
  status: LabValue["status"];
  unit: string;
}

export function LabTrendChart({ testAbbrev, apiClient }: Props) {
  const { data: results = [], isLoading } = useLabResults({ test: testAbbrev }, apiClient);

  if (isLoading) {
    return <div className="h-64 w-full animate-pulse rounded-md bg-muted" />;
  }

  const numeric = results.filter((r) => r.value != null) as Array<LabValue & { value: number }>;
  if (numeric.length === 0) {
    return (
      <EmptyState
        title="No data yet"
        body="We'll show a trend here once you add some lab values for this test."
      />
    );
  }

  // Recharts wants chronological order (ascending)
  const chartData: ChartPoint[] = [...numeric]
    .reverse()
    .map((r) => ({
      date: r.measured_at ?? r.created_at.slice(0, 10),
      label: formatShortDate(r.measured_at ?? r.created_at),
      value: r.value,
      status: r.status,
      unit: r.unit,
    }));

  const latest = numeric[0];
  const refMin = latest.reference_min;
  const refMax = latest.reference_max;

  // Compute Y-axis domain that leaves room above/below the reference band
  const values = chartData.map((p) => p.value);
  let yMin = Math.min(...values, refMin ?? Infinity);
  let yMax = Math.max(...values, refMax ?? -Infinity);
  const pad = (yMax - yMin) * 0.15 || yMax * 0.1 || 1;
  yMin = Math.max(0, yMin - pad);
  yMax = yMax + pad;

  if (chartData.length === 1) {
    return (
      <div>
        <SinglePoint point={chartData[0]} refMin={refMin} refMax={refMax} />
        <p className="mt-3 text-xs text-muted-foreground">
          Not enough data for a trend yet — add more measurements to see how this changes over time.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Legend caption: "Normal range" swatch + numeric bounds live OUTSIDE
          the chart so they stay readable regardless of the curve's shape.
          Matches the dashed style used for the ReferenceLines below. */}
      {(refMin != null || refMax != null) && (
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <svg width="16" height="8" aria-hidden="true" className="shrink-0">
            <line
              x1="0"
              y1="4"
              x2="16"
              y2="4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeDasharray="4 3"
            />
          </svg>
          <span>
            Normal range:{" "}
            <span className="font-mono text-foreground">
              {refMin != null && refMax != null
                ? `${fmtNum(refMin)}–${fmtNum(refMax)}`
                : refMax != null
                  ? `< ${fmtNum(refMax)}`
                  : `> ${fmtNum(refMin!)}`}{" "}
              {latest.unit}
            </span>
          </span>
        </div>
      )}

      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {/*
            Left-align the plot:
            - margin.left = -24 pulls the YAxis labels into the container's
              left padding, so the curve itself starts right at the edge
            - XAxis padding adds 8px breathing room on each end so the
              first/last circles don't clip the plot boundary
            - Reference range shown as two horizontal dashed lines (not a
              rectangular band) so the gradient fill under the curve reads
              as "area under the curve" without competing with the band.
          */}
          <AreaChart data={chartData} margin={{ top: 12, right: 12, left: -24, bottom: 8 }}>
          <defs>
            {/* Gradient fill under the curve: brand blue at top fading to
                transparent at the bottom. Clipped by the curve (Area
                element handles this), so it reads as "area under the curve"
                rather than a rectangular band. */}
            <linearGradient id="labTrendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--brand-700))" stopOpacity={0.25} />
              <stop offset="100%" stopColor="hsl(var(--brand-700))" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="label"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            tickMargin={6}
            padding={{ left: 8, right: 8 }}
          />
          <YAxis
            domain={[yMin, yMax]}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            width={40}
            tickMargin={2}
          />

          {/* Reference range — horizontal dashed lines at min/max.
              Neutral muted-foreground (not green) so they don't blend into
              the blue gradient fill; full opacity and 1.5px so they're
              clearly visible. Numeric labels live in the legend caption
              above the chart, not inside the plot. */}
          {refMin != null && (
            <ReferenceLine
              y={refMin}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="4 3"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />
          )}
          {refMax != null && (
            <ReferenceLine
              y={refMax}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="4 3"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />
          )}

          <Tooltip
            cursor={{ stroke: "hsl(var(--muted-foreground))", strokeWidth: 1, strokeDasharray: "3 3" }}
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
              padding: "6px 10px",
            }}
            labelStyle={{
              color: "hsl(var(--foreground))",
              fontWeight: 600,
              marginBottom: 2,
            }}
            itemStyle={{ color: "hsl(var(--foreground))", padding: 0 }}
            // Header line: use the raw ISO date field from the payload for a
            // human-readable "March 15, 2026" instead of the short axis label.
            labelFormatter={(_label, payload) => {
              const first = Array.isArray(payload) && payload.length > 0 ? payload[0] : null;
              const iso =
                (first?.payload as ChartPoint | undefined)?.date ?? (_label as string);
              if (!iso) return "";
              const d = new Date(iso);
              if (Number.isNaN(d.getTime())) return String(_label);
              return d.toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              });
            }}
            formatter={(value, _name, item) => {
              const unit = (item as unknown as { payload?: ChartPoint }).payload?.unit ?? "";
              const display = typeof value === "number" ? fmtNum(value) : value;
              return [`${display} ${unit}`, "Value"];
            }}
          />

          <Area
            type="monotone"
            dataKey="value"
            stroke="hsl(var(--brand-700))"
            strokeWidth={2}
            fill="url(#labTrendFill)"
            fillOpacity={1}
            // Larger filled circles with a background-coloured stroke so they
            // stand out against the curve and the gradient fill underneath.
            dot={(dotProps) => {
              const { cx, cy, payload, key } = dotProps as {
                cx: number;
                cy: number;
                payload: ChartPoint;
                key?: string;
              };
              const color =
                payload.status === "in_range"
                  ? "hsl(var(--success-700))"
                  : payload.status === "unknown"
                    ? "hsl(var(--muted-foreground))"
                    : "hsl(var(--warning-700))";
              return (
                <Dot
                  key={key}
                  cx={cx}
                  cy={cy}
                  r={5}
                  fill={color}
                  stroke="hsl(var(--background))"
                  strokeWidth={2}
                />
              );
            }}
            activeDot={{
              r: 7,
              stroke: "hsl(var(--background))",
              strokeWidth: 2,
            }}
          />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function fmtNum(n: number): string {
  return String(Number(n.toFixed(2)));
}

function SinglePoint({
  point,
  refMin,
  refMax,
}: {
  point: ChartPoint;
  refMin: number | null;
  refMax: number | null;
}) {
  return (
    <div className="rounded-md border border-border bg-card p-6">
      <p className="text-xs text-muted-foreground">{point.label}</p>
      <p className="mt-1 font-mono text-3xl font-semibold text-foreground">
        {fmtNum(point.value)} <span className="text-base text-muted-foreground">{point.unit}</span>
      </p>
      {(refMin != null || refMax != null) && (
        <p className="mt-1 text-xs text-muted-foreground">
          Normal range:{" "}
          {refMin != null && refMax != null
            ? `${fmtNum(refMin)}–${fmtNum(refMax)}`
            : refMax != null
              ? `< ${fmtNum(refMax)}`
              : `> ${fmtNum(refMin!)}`}{" "}
          {point.unit}
        </p>
      )}
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-card p-8 text-center">
      <p className="text-base font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

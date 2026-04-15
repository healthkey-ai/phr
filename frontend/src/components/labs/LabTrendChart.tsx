/**
 * LabTrendChart — full time-series view of a single lab over time.
 * Per docs/patient-app-design.md §4.2 + §5.8.
 *
 * - Recharts line chart
 * - Reference range as shaded horizontal band
 * - Out-of-range points highlighted via status colour
 * - Empty state: < 1 data point → "Not enough data for a trend yet"
 * - Partial state: exactly 1 data point → render a single dot
 */
import {
  CartesianGrid,
  Dot,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useLabResults } from "@/features/labs/api";
import type { LabResult } from "@/types/labs";

interface Props {
  testAbbrev: string;
}

interface ChartPoint {
  date: string;           // YYYY-MM-DD
  label: string;          // "Mar 15"
  value: number;
  status: LabResult["status"];
  unit: string;
}

export function LabTrendChart({ testAbbrev }: Props) {
  const { data: results = [], isLoading } = useLabResults({ test: testAbbrev });

  if (isLoading) {
    return <div className="h-64 w-full animate-pulse rounded-md bg-muted" />;
  }

  const numeric = results.filter((r) => r.value != null) as Array<LabResult & { value: number }>;
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
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="label"
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
          />
          <YAxis
            domain={[yMin, yMax]}
            stroke="hsl(var(--muted-foreground))"
            fontSize={11}
            width={40}
          />

          {/* Reference range — shaded band */}
          {refMin != null && refMax != null && (
            <ReferenceArea
              y1={refMin}
              y2={refMax}
              fill="hsl(var(--success-50))"
              fillOpacity={0.6}
              stroke="none"
            />
          )}

          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
            formatter={(value, _name, item) => {
              const unit = (item as unknown as { payload?: ChartPoint }).payload?.unit ?? "";
              return [`${value} ${unit}`, "Value"];
            }}
          />

          <Line
            type="monotone"
            dataKey="value"
            stroke="hsl(var(--brand-700))"
            strokeWidth={2}
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
              return <Dot key={key} cx={cx} cy={cy} r={4} fill={color} stroke="none" />;
            }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
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
        {point.value} <span className="text-base text-muted-foreground">{point.unit}</span>
      </p>
      {refMin != null && refMax != null && (
        <p className="mt-1 text-xs text-muted-foreground">
          Normal range: {refMin}–{refMax} {point.unit}
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

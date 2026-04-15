/**
 * LabValueCard — single lab value with value, unit, reference range, sparkline,
 * provenance badge.
 *
 * Per docs/patient-app-design.md §4.2. Phase 2a wires it to real data from the
 * /labs/results/ endpoint via a test abbreviation.
 */
import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";

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
  const trend = getTrend(latest, previous);

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-base font-semibold text-foreground">
            {title ?? latest.test.name}
          </h3>
          <TrendIcon trend={trend} />
        </div>

        <div className="flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold text-foreground">
            {formatValue(latest)}
          </span>
          {latest.unit && (
            <span className="text-sm text-muted-foreground">{latest.unit}</span>
          )}
        </div>

        {latest.reference_min != null && latest.reference_max != null && (
          <p className="mt-1 text-xs text-muted-foreground">
            Normal: {latest.reference_min}–{latest.reference_max} {latest.unit}
          </p>
        )}

        {/* Sparkline: show last 6 points if we have them */}
        {results.length > 1 && <Sparkline results={results.slice(0, 6).reverse()} />}

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
  );
}

function formatValue(r: LabResult): string {
  if (r.value != null) {
    // Keep 1-2 decimals for readability; drop trailing zeros
    return String(Number(r.value.toFixed(2)));
  }
  return r.value_qualitative || "—";
}

function getTrend(latest: LabResult, prev?: LabResult): "up" | "down" | "flat" | null {
  if (!prev || latest.value == null || prev.value == null) return null;
  const delta = latest.value - prev.value;
  const pct = Math.abs(delta) / (Math.abs(prev.value) || 1);
  if (pct < 0.02) return "flat";
  return delta > 0 ? "up" : "down";
}

function TrendIcon({ trend }: { trend: "up" | "down" | "flat" | null }) {
  if (!trend) return null;
  if (trend === "up") return <ArrowUp className="h-4 w-4 text-muted-foreground" />;
  if (trend === "down") return <ArrowDown className="h-4 w-4 text-muted-foreground" />;
  return <ArrowRight className="h-4 w-4 text-muted-foreground" />;
}

function StatusChip({ status }: { status: LabResult["status"] }) {
  const styles: Record<LabResult["status"], string> = {
    in_range: "bg-success-50 text-success-700 border-success-200",
    below: "bg-warning-50 text-warning-700 border-warning-200",
    above: "bg-warning-50 text-warning-700 border-warning-200",
    unknown: "bg-muted text-muted-foreground border-border",
  };
  const labels: Record<LabResult["status"], string> = {
    in_range: "Normal",
    below: "Below",
    above: "Above",
    unknown: "No range",
  };
  return (
    <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

/** Inline sparkline of last N values — no axes, pure shape indicator. */
function Sparkline({ results }: { results: LabResult[] }) {
  const values = results.map((r) => r.value).filter((v): v is number => v != null);
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 120;
  const h = 24;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-3 h-6 w-full text-healthkey-brand-700"
      role="img"
      aria-label="Recent values trend"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
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

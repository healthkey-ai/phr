/**
 * DataSourceBadge — provenance chip per docs/patient-app-design.md §4.2.
 * Always shown next to health data so the user knows where it came from.
 */
type Source = "fhir" | "manual" | "ai" | "document" | "wearable";

interface Props {
  source: Source;
  detail?: string;
  timeAgo?: string;
  confidence?: number;
}

const SOURCE_LABELS: Record<Source, string> = {
  fhir: "FHIR",
  manual: "Manual",
  ai: "AI",
  document: "Document",
  wearable: "Wearable",
};

export function DataSourceBadge({ source, detail, timeAgo, confidence }: Props) {
  const parts: string[] = [SOURCE_LABELS[source]];
  if (detail) parts.push(detail);
  if (typeof confidence === "number") parts.push(`${Math.round(confidence * 100)}% confident`);
  if (timeAgo) parts.push(timeAgo);

  return (
    <span
      className="inline-flex items-center rounded-sm border border-border bg-muted px-2 py-0.5 text-caption text-muted-foreground"
      aria-label={`Source: ${parts.join(", ")}`}
    >
      {parts.join(" · ")}
    </span>
  );
}

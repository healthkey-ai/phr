/**
 * FileSourceBadge — provenance chip for lab results that originated from an
 * uploaded report. Shows the source PDF filename instead of the generic
 * "Document" label.
 *
 * Filenames can be long (`ExactSciences-LabReport-2026-03-15-Patient-12345.pdf`),
 * so the filename span truncates with ellipsis inside a bounded flex parent.
 * The full filename is available on hover via the `title` attribute. Any
 * trailing timeAgo stays fully visible to the right.
 */
import { FileText } from "lucide-react";

interface Props {
  filename: string;
  timeAgo?: string;
  /** Cap on the badge's overall width (Tailwind class). Ignored when `truncate` is false. */
  maxWidthClass?: string;
  /**
   * When true (default) the filename clips with ellipsis inside the
   * `maxWidthClass` bound. When false the badge renders the full filename,
   * wrapping onto multiple lines if needed.
   */
  truncate?: boolean;
  /**
   * When true the badge renders as a `flex w-full` block that spans the
   * parent's width, with filename + timeAgo on opposite ends and the
   * filename wrapping inside. Implies `truncate=false`.
   */
  fullWidth?: boolean;
}

export function FileSourceBadge({
  filename,
  timeAgo,
  maxWidthClass = "max-w-[220px]",
  truncate = true,
  fullWidth = false,
}: Props) {
  if (fullWidth) {
    return (
      <span
        className="flex w-full items-center gap-1.5 rounded-sm border border-border bg-muted px-2 py-0.5 text-caption text-muted-foreground"
        title={filename}
        aria-label={`Source: Document, ${filename}${timeAgo ? `, ${timeAgo}` : ""}`}
      >
        <FileText className="h-3 w-3 shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate">{filename}</span>
        {timeAgo && (
          <span className="shrink-0 whitespace-nowrap">· {timeAgo}</span>
        )}
      </span>
    );
  }
  if (!truncate) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-sm border border-border bg-muted px-2 py-0.5 text-caption text-muted-foreground"
        aria-label={`Source: Document, ${filename}${timeAgo ? `, ${timeAgo}` : ""}`}
      >
        <FileText className="h-3 w-3 shrink-0" aria-hidden="true" />
        <span className="break-all">{filename}</span>
        {timeAgo && <span className="whitespace-nowrap">· {timeAgo}</span>}
      </span>
    );
  }
  return (
    <span
      className={`inline-flex min-w-0 ${maxWidthClass} items-center gap-1 rounded-sm border border-border bg-muted px-2 py-0.5 text-caption text-muted-foreground`}
      title={filename}
      aria-label={`Source: Document, ${filename}${timeAgo ? `, ${timeAgo}` : ""}`}
    >
      <FileText className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span className="min-w-0 truncate">{filename}</span>
      {timeAgo && <span className="shrink-0 whitespace-nowrap">· {timeAgo}</span>}
    </span>
  );
}

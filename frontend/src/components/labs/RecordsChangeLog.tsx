/**
 * RecordsChangeLog — audit feed of everything the patient has done to their
 * record (uploads, manual lab entries). Rendered collapsed at the bottom of
 * the Records page.
 *
 * Uploads are grouped by filename so re-uploading the same report stacks
 * under one header instead of scattering identical filenames through the feed.
 */
import { useState } from "react";
import { FileText, PenLine, Trash2, Upload as UploadIcon } from "lucide-react";

import { useDeleteLabUpload, useLabResults, useLabUploads } from "@/features/labs/api";
import type { LabValue, UploadJob, UploadFile } from "@/types/labs";

interface UploadEvent {
  upload: UploadJob;
  file: UploadFile;
  /** LabResults actually committed from this upload — the real "saved" count. */
  savedCount: number;
}

export function RecordsChangeLog() {
  const { data: uploads = [], isLoading: uploadsLoading } = useLabUploads();
  const { data: results = [], isLoading: resultsLoading } = useLabResults();
  const deleteUpload = useDeleteLabUpload();

  const isLoading = uploadsLoading || resultsLoading;

  // Count saved LabResults per upload id — this is the real "values added"
  // figure for the change log. parsed_results[].accepted stays at extractor
  // defaults forever; commit() never writes back to it.
  const savedPerUpload = new Map<number, number>();
  for (const r of results) {
    if (r.upload != null) {
      savedPerUpload.set(r.upload, (savedPerUpload.get(r.upload) ?? 0) + 1);
    }
  }

  const uploadGroups = groupUploadsByFilename(uploads, savedPerUpload);
  const manualResults = results
    .filter((r) => r.source === "manual")
    .slice()
    .sort(
      (a, b) =>
        new Date(b.measured_at ?? b.created_at).getTime() -
        new Date(a.measured_at ?? a.created_at).getTime(),
    );

  const totalEvents = sumUploadEvents(uploadGroups) + manualResults.length;

  return (
    <details className="group mt-10 rounded-md border border-border bg-card">
      <summary className="flex cursor-pointer select-none list-none items-center justify-between gap-2 rounded-md px-5 py-4 text-h4 text-foreground hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-healthkey-brand-700">
        <span>Change log</span>
        <span className="text-xs font-normal text-muted-foreground">
          {isLoading
            ? "Loading…"
            : totalEvents === 0
              ? "No changes yet"
              : `${totalEvents} ${totalEvents === 1 ? "entry" : "entries"}`}
          <span className="ml-2 inline-block transition-transform group-open:rotate-180">
            ▾
          </span>
        </span>
      </summary>

      <div className="border-t border-border px-5 py-4 text-sm">
        {isLoading ? (
          <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        ) : totalEvents === 0 ? (
          <p className="text-body text-muted-foreground">
            Your uploads and manual entries will appear here.
          </p>
        ) : (
          <div className="space-y-6">
            {uploadGroups.length > 0 && (
              <section>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <UploadIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  Uploads
                </h3>
                <ul className="space-y-3">
                  {uploadGroups.map((group) => (
                    <li key={group.filename}>
                      <FileGroup
                        group={group}
                        onDelete={(uploadId) => deleteUpload.mutate(uploadId)}
                        deletingId={deleteUpload.variables}
                        isDeleting={deleteUpload.isPending}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {manualResults.length > 0 && (
              <section>
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <PenLine className="h-3.5 w-3.5" aria-hidden="true" />
                  Manual entries
                </h3>
                <ul className="space-y-1.5">
                  {manualResults.map((r) => (
                    <li
                      key={r.id}
                      className="flex items-baseline justify-between gap-4 text-body"
                    >
                      <span className="min-w-0 truncate text-foreground">
                        <span className="font-medium">{r.test.name}</span>
                        <span className="ml-1 text-muted-foreground">
                          {formatResultValue(r)}
                        </span>
                      </span>
                      <span className="shrink-0 whitespace-nowrap font-mono text-xs text-muted-foreground">
                        {formatDate(r.measured_at ?? r.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>
    </details>
  );
}

interface FilenameGroup {
  filename: string;
  events: UploadEvent[];
  latestDate: string;
}

function groupUploadsByFilename(
  uploads: UploadJob[],
  savedPerUpload: Map<number, number>,
): FilenameGroup[] {
  const map = new Map<string, UploadEvent[]>();

  for (const upload of uploads) {
    const savedCount = savedPerUpload.get(upload.id) ?? 0;

    for (const file of upload.files ?? []) {
      const key = file.original_filename || "Untitled upload";
      const entry: UploadEvent = { upload, file, savedCount };
      const bucket = map.get(key);
      if (bucket) bucket.push(entry);
      else map.set(key, [entry]);
    }
  }

  return Array.from(map.entries())
    .map(([filename, events]) => {
      events.sort(
        (a, b) =>
          new Date(b.upload.created_at).getTime() -
          new Date(a.upload.created_at).getTime(),
      );
      return { filename, events, latestDate: events[0].upload.created_at };
    })
    .sort(
      (a, b) =>
        new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime(),
    );
}

function FileGroup({
  group,
  onDelete,
  deletingId,
  isDeleting,
}: {
  group: FilenameGroup;
  onDelete: (uploadId: number) => void;
  deletingId: number | undefined;
  isDeleting: boolean;
}) {
  const [confirmId, setConfirmId] = useState<number | null>(null);

  return (
    <div>
      <div className="flex items-baseline gap-2">
        <FileText
          className="h-4 w-4 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <span className="min-w-0 break-all font-medium text-foreground">
          {group.filename}
        </span>
        {group.events.length > 1 && (
          <span className="shrink-0 text-xs text-muted-foreground">
            · {group.events.length} uploads
          </span>
        )}
      </div>
      <ul className="mt-1 ml-6 space-y-1">
        {group.events.map((e) => {
          const busy = isDeleting && deletingId === e.upload.id;
          const confirming = confirmId === e.upload.id;
          return (
            <li
              key={e.upload.id + ":" + e.file.id}
              className="flex items-baseline justify-between gap-4 text-body"
            >
              <span className="min-w-0 text-muted-foreground">
                <StatusLabel event={e} />
              </span>
              <span className="flex shrink-0 items-center gap-2">
                {confirming ? (
                  <>
                    <button
                      className="text-xs text-destructive hover:underline disabled:opacity-50"
                      disabled={busy}
                      onClick={() => {
                        onDelete(e.upload.id);
                        setConfirmId(null);
                      }}
                    >
                      {busy ? "Deleting…" : "Confirm delete"}
                    </button>
                    <button
                      className="text-xs text-muted-foreground hover:underline"
                      onClick={() => setConfirmId(null)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="text-muted-foreground/60 hover:text-destructive transition-colors"
                    title="Delete upload and its lab values"
                    onClick={() => setConfirmId(e.upload.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
                <span className="whitespace-nowrap font-mono text-xs text-muted-foreground">
                  {formatDate(e.upload.created_at)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function StatusLabel({ event }: { event: UploadEvent }) {
  const { upload, savedCount } = event;
  if (upload.status === "failed") {
    return <span className="text-warning-700">Extraction failed</span>;
  }
  if (upload.status === "pending" || upload.status === "processing") {
    return <span>Processing…</span>;
  }
  // completed
  if (savedCount > 0) {
    return (
      <span>
        {savedCount} {savedCount === 1 ? "value" : "values"} saved
      </span>
    );
  }
  return <span>No values saved</span>;
}

function sumUploadEvents(groups: FilenameGroup[]): number {
  return groups.reduce((acc, g) => acc + g.events.length, 0);
}

function formatResultValue(r: LabValue): string {
  if (r.value != null) {
    const n = Number(r.value.toFixed(2));
    return r.unit ? `${n} ${r.unit}` : String(n);
  }
  return r.value_qualitative || "—";
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

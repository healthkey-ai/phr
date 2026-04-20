/**
 * LabUploadDialog — Phase 2b file upload flow.
 *
 * State machine:
 *   picker  → patient picks 1..10 files + optional lab_date / notes, taps Upload
 *   uploading → POST in flight (button spinner, form disabled)
 *   processing → polling GET /uploads/{id}/ every 2s for status transitions
 *   done    → stub task completed. Phase 2b UX endpoint — "files saved; reading
 *             is coming in the next release." Phase 2c replaces `done` with a
 *             routable transition into the review screen.
 *   failed  → error surface with retry / cancel.
 *
 * No review / commit yet — that's Phase 2d. The dialog intentionally stops at
 * `done` for Phase 2b so the patient sees evidence their files landed safely
 * without being promised extraction that doesn't exist yet.
 */
import { useRef, useState } from "react";
import { Loader2, Paperclip, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { useCreateLabUpload, useLabUpload, useRetryExtraction } from "@/features/labs/api";
import type { LabUpload, LabUploadCommitResponse } from "@/types/labs";
import { LabUploadReview } from "./LabUploadReview";

const MAX_FILES = 10;
const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB — must match backend
const MAX_TOTAL_BYTES = 20 * 1024 * 1024;
const ACCEPT_ATTR = "application/pdf,image/jpeg,image/png,image/heic";
const ACCEPT_EXT = [".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif"];

type Phase =
  | "picker"      // pick files + metadata
  | "uploading"   // POST /uploads/ in flight
  | "processing"  // polling /uploads/{id}/ for extraction
  | "reviewing"   // Phase 2d: review extracted rows + save
  | "done"        // commit succeeded, show N saved
  | "failed";     // extraction failed — retry or cancel

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function LabUploadDialog({ open, onOpenChange }: Props) {
  const [phase, setPhase] = useState<Phase>("picker");
  const [files, setFiles] = useState<File[]>([]);
  const [labDate, setLabDate] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [completedUpload, setCompletedUpload] = useState<LabUpload | null>(null);
  const [commitResponse, setCommitResponse] = useState<LabUploadCommitResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const createUpload = useCreateLabUpload();
  const retryExtraction = useRetryExtraction();

  // Poll the upload once we have an id and we're in processing phase.
  // Stops automatically when status flips to completed/failed (see hook).
  const { data: polled } = useLabUpload(uploadId, phase === "processing");

  // Transition out of `processing` when the polled upload reports a terminal state.
  // Phase 2d: a completed upload now lands on the review screen, not straight to done.
  if (phase === "processing" && polled) {
    if (polled.status === "completed") {
      setCompletedUpload(polled);
      setPhase("reviewing");
    } else if (polled.status === "failed") {
      setServerError(polled.error_message || "Something went wrong reading your report.");
      setPhase("failed");
    }
  }

  function reset() {
    setPhase("picker");
    setFiles([]);
    setLabDate("");
    setNotes("");
    setClientError(null);
    setServerError(null);
    setUploadId(null);
    setCompletedUpload(null);
    setCommitResponse(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleClose(next: boolean) {
    if (!next) {
      // Closing — reset state so reopening is fresh
      reset();
    }
    onOpenChange(next);
  }

  function handleFilesPicked(picked: FileList | null) {
    if (!picked || picked.length === 0) return;
    setClientError(null);

    const merged = [...files];
    for (const f of Array.from(picked)) {
      if (merged.length >= MAX_FILES) {
        setClientError(`You can upload up to ${MAX_FILES} files at once.`);
        break;
      }
      if (f.size > MAX_FILE_BYTES) {
        setClientError(
          `"${f.name}" is ${humanBytes(f.size)}. Max ${humanBytes(MAX_FILE_BYTES)} per file.`,
        );
        continue;
      }
      const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
      if (!ACCEPT_EXT.includes(ext)) {
        setClientError(
          `"${f.name}" isn't a PDF, JPEG, PNG, or HEIC. Convert it or pick another file.`,
        );
        continue;
      }
      // Skip duplicates by name+size (cheap pre-SHA dedup on the client)
      if (merged.some((m) => m.name === f.name && m.size === f.size)) continue;
      merged.push(f);
    }

    const nextTotal = merged.reduce((sum, f) => sum + f.size, 0);
    if (nextTotal > MAX_TOTAL_BYTES) {
      setClientError(
        `Total is ${humanBytes(nextTotal)}. Max ${humanBytes(MAX_TOTAL_BYTES)} per upload.`,
      );
      return;
    }

    setFiles(merged);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setClientError(null);
  }

  async function handleRetry() {
    setServerError(null);
    // If we have an uploadId we can re-run extraction server-side. Otherwise
    // drop back to the picker — the patient never got as far as creating one.
    if (uploadId === null) {
      setPhase("picker");
      return;
    }
    try {
      const fresh = await retryExtraction.mutateAsync(uploadId);
      if (fresh.status === "completed") {
        setCompletedUpload(fresh);
        setPhase("reviewing");
      } else if (fresh.status === "failed") {
        setServerError(fresh.error_message || "Still couldn't read this report.");
        setPhase("failed");
      } else {
        setPhase("processing");
      }
    } catch (err) {
      setServerError(extractErrorMessage(err));
    }
  }

  async function handleSubmit() {
    if (files.length === 0) {
      setClientError("Pick at least one file to upload.");
      return;
    }
    setPhase("uploading");
    setServerError(null);
    try {
      const upload = await createUpload.mutateAsync({
        files,
        lab_date: labDate || undefined,
        notes: notes || undefined,
      });
      setUploadId(upload.id);
      // If the backend returned a terminal status (eager mode in dev, or stub
      // finished instantly), skip the "processing" screen and go straight
      // to review. Only fatal failures short-circuit to the error surface.
      if (upload.status === "completed") {
        setCompletedUpload(upload);
        setPhase("reviewing");
      } else if (upload.status === "failed") {
        setServerError(upload.error_message || "Something went wrong reading your report.");
        setPhase("failed");
      } else {
        setPhase("processing");
      }
    } catch (err: unknown) {
      const msg = extractErrorMessage(err);
      setServerError(msg);
      setPhase("failed");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      {/* Flex column with capped height:
          - min-w-0 lets the grid cell shrink below content width so long
            filenames wrap instead of blowing out max-w-lg
          - max-h-[85vh] + flex-col lets the middle body scroll without
            pushing the dialog off the screen
          - flex (vs shadcn's default grid) gives us predictable sizing:
            header + footer are shrink-0, the body in between takes flex-1 */}
      <DialogContent className="flex max-h-[85vh] min-w-0 flex-col gap-4 sm:max-w-lg">
        <DialogHeader className="min-w-0 shrink-0">
          <DialogTitle>{titleFor(phase)}</DialogTitle>
          <DialogDescription>{descriptionFor(phase)}</DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
        {phase === "picker" && (
          <div className="space-y-4">
            {/* File list + drop zone. Drop zone stays visible the whole
                time the patient is in the picker — disappearing it after
                the first file lands is confusing (where did the drop
                target go?) and forces them to hunt for a small "Add
                another file" link. Only hidden once they hit MAX_FILES. */}
            <div>
              <Label className="mb-2 block">Files</Label>
              {files.length > 0 && (
                <div className="mb-2 space-y-2">
                  {files.map((f, i) => (
                    <FileChip
                      key={`${f.name}-${i}`}
                      name={f.name}
                      size={f.size}
                      onRemove={() => removeFile(i)}
                    />
                  ))}
                </div>
              )}
              {files.length < MAX_FILES && (
                <DropZone
                  compact={files.length > 0}
                  onPick={() => fileInputRef.current?.click()}
                  onFilesDropped={(list) => handleFilesPicked(list)}
                />
              )}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={ACCEPT_ATTR}
                className="hidden"
                onChange={(e) => handleFilesPicked(e.target.files)}
              />
              <p className="mt-2 text-caption text-muted-foreground">
                PDF, JPEG, PNG, or HEIC. Up to {MAX_FILES} files, {humanBytes(MAX_FILE_BYTES)} each,{" "}
                {humanBytes(MAX_TOTAL_BYTES)} total.
              </p>
            </div>

            {/* Lab date */}
            <div>
              <Label htmlFor="lab_date" className="mb-2 block">
                Report date (optional)
              </Label>
              <Input
                id="lab_date"
                type="date"
                value={labDate}
                onChange={(e) => setLabDate(e.target.value)}
              />
            </div>

            {/* Notes */}
            <div>
              <Label htmlFor="notes" className="mb-2 block">
                Notes (optional)
              </Label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. follow-up CBC from Dr. Chen"
                rows={2}
                maxLength={2000}
                className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-body ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
            </div>

            {clientError && (
              <p className="text-caption text-error-700" role="alert">
                {clientError}
              </p>
            )}
            {serverError && (
              <p className="text-caption text-error-700" role="alert">
                {serverError}
              </p>
            )}
          </div>
        )}

        {(phase === "uploading" || phase === "processing") && (
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-brand-700" />
              <p className="text-body text-foreground">
                {phase === "uploading" ? "Uploading your files…" : "Reading your report…"}
              </p>
            </div>
            <Progress value={phase === "uploading" ? 40 : 80} />
            <p className="text-caption text-muted-foreground">
              This usually takes 10–30 seconds.
            </p>
          </div>
        )}

        {phase === "reviewing" && completedUpload && (
          <LabUploadReview
            upload={completedUpload}
            onCancel={() => handleClose(false)}
            onSaved={(response) => {
              setCommitResponse(response);
              setPhase("done");
            }}
          />
        )}

        {phase === "done" && (
          <DoneSummary
            files={files}
            upload={completedUpload}
            commit={commitResponse}
          />
        )}

        {phase === "failed" && (
          <div className="space-y-3 py-2">
            <p className="text-body text-error-700" role="alert">
              {serverError || "Something went wrong. Please try again."}
            </p>
          </div>
        )}
        </div>

        {/* The reviewing phase manages its own footer via LabUploadReview. */}
        {phase !== "reviewing" && (
          <DialogFooter className="shrink-0">
            {phase === "picker" && (
              <>
                <Button type="button" variant="ghost" onClick={() => handleClose(false)}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleSubmit}
                  disabled={files.length === 0 || createUpload.isPending}
                >
                  <Upload className="mr-1 h-4 w-4" />
                  Upload{files.length > 1 ? ` ${files.length} files` : ""}
                </Button>
              </>
            )}
            {(phase === "uploading" || phase === "processing") && (
              <Button type="button" variant="ghost" disabled>
                Uploading…
              </Button>
            )}
            {phase === "done" && (
              <Button type="button" onClick={() => handleClose(false)}>
                Done
              </Button>
            )}
            {phase === "failed" && (
              <>
                <Button type="button" variant="ghost" onClick={() => handleClose(false)}>
                  Close
                </Button>
                <Button
                  type="button"
                  onClick={handleRetry}
                  disabled={retryExtraction.isPending}
                >
                  {retryExtraction.isPending && (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  )}
                  Try again
                </Button>
              </>
            )}
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Subcomponents ────────────────────────────────────────────────────────────

function DoneSummary({
  files,
  upload,
  commit,
}: {
  files: File[];
  upload: LabUpload | null;
  commit: LabUploadCommitResponse | null;
}) {
  const saved = commit?.saved_count ?? 0;
  const skipped = commit?.skipped_count ?? 0;
  const totalParsed = upload?.parsed_results?.length ?? 0;
  const filesCopy = files.length === 1 ? "file" : `${files.length} files`;

  // No extraction happened — patient went through review but there was nothing
  // to review. Surface manual-entry as the next step.
  if (totalParsed === 0) {
    return (
      <div className="space-y-3 py-2">
        <p className="text-body text-foreground">Your {filesCopy} saved.</p>
        <p className="text-caption text-muted-foreground">
          We couldn't find any lab values on this report. You can still enter values manually
          via <span className="font-semibold">Add lab result</span>.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 py-2">
      <p className="text-body text-foreground">
        Saved <span className="font-semibold">{saved}</span>{" "}
        {saved === 1 ? "result" : "results"} to your record.
      </p>
      {skipped > 0 && (
        <p className="text-caption text-muted-foreground">
          {skipped} {skipped === 1 ? "row was" : "rows were"} skipped as duplicates of values
          already saved.
        </p>
      )}
      <p className="text-caption text-muted-foreground">
        Your new values are in the Records tab. Upload more reports or add values manually
        anytime.
      </p>
    </div>
  );
}

function DropZone({
  onPick,
  onFilesDropped,
  compact,
}: {
  onPick: () => void;
  onFilesDropped: (files: FileList) => void;
  compact: boolean;
}) {
  const [dragging, setDragging] = useState(false);

  // HTML5 drag-and-drop: dragenter/dragover must preventDefault to signal
  // we accept drops on this element; without it the browser blocks the
  // drop event entirely. dragleave can fire spuriously when hovering over
  // child elements, so we track a counter instead of a single boolean.
  const dragDepth = useRef(0);

  function handleDragEnter(e: React.DragEvent<HTMLButtonElement>) {
    e.preventDefault();
    dragDepth.current += 1;
    setDragging(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLButtonElement>) {
    e.preventDefault();
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setDragging(false);
    }
  }

  function handleDragOver(e: React.DragEvent<HTMLButtonElement>) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(e: React.DragEvent<HTMLButtonElement>) {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    if (e.dataTransfer.files?.length) {
      onFilesDropped(e.dataTransfer.files);
    }
  }

  const base =
    "flex w-full flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed transition";
  const padding = compact ? "px-4 py-4" : "px-4 py-8";
  const tone = dragging
    ? "border-brand-700 bg-brand-50 text-brand-700"
    : "border-muted-foreground/30 bg-muted/30 text-muted-foreground hover:border-brand-700/40 hover:bg-muted/50 hover:text-foreground";

  return (
    <button
      type="button"
      onClick={onPick}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`${base} ${padding} ${tone}`}
    >
      <Paperclip className={compact ? "h-4 w-4" : "h-6 w-6"} />
      <span className="text-body">
        {compact ? "Add another file" : dragging ? "Drop to upload" : "Tap to pick files"}
      </span>
      {!compact && (
        <span className="text-caption">
          {dragging ? " " : "or drag them here"}
        </span>
      )}
    </button>
  );
}

function FileChip({
  name,
  size,
  onRemove,
}: {
  name: string;
  size: number;
  onRemove: () => void;
}) {
  // Filename WRAPS rather than truncating — long lab-report names from
  // Downloads ("Amniotic-fluid-AFP-AChE-normal-rep-717-v1-1012.pdf") are
  // informative, so the patient benefits from seeing the whole thing. The
  // row grows vertically; the dialog's outer max-h + scroll container
  // keep it from blowing past the viewport.
  //
  // `break-all` breaks at any character — important because many lab PDF
  // filenames are long hyphenated strings that `break-words` wouldn't
  // split early enough to avoid pushing past the chip edge.
  // `items-start` + the small `mt-0.5` on the paperclip / size keep them
  // aligned with the first line of the name when it wraps.
  return (
    <div className="flex items-start gap-3 rounded-md border border-border bg-muted/30 px-3 py-2">
      <Paperclip className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
      <span
        className="min-w-0 flex-1 break-all text-body text-foreground"
        title={name}
      >
        {name}
      </span>

      <span className="mt-0.5 flex-shrink-0 text-caption text-muted-foreground">
        {humanBytes(size)}
      </span>
      <button
        type="button"
        onClick={onRemove}
        className="flex-shrink-0 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        aria-label={`Remove ${name}`}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function humanBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
}

function titleFor(phase: Phase): string {
  switch (phase) {
    case "picker":
      return "Upload lab report";
    case "uploading":
    case "processing":
      return "Reading your report…";
    case "reviewing":
      return "Review extracted results";
    case "done":
      return "Results saved";
    case "failed":
      return "Upload failed";
  }
}

function descriptionFor(phase: Phase): string {
  switch (phase) {
    case "picker":
      return "Pick one or more files from your device. We'll read them and surface the lab values for review.";
    case "uploading":
    case "processing":
      return "You can leave this screen — we'll have your values ready when you come back.";
    case "reviewing":
      return "Confirm the values we found. Uncheck anything you don't want saved.";
    case "done":
      return "Your Records tab now reflects the new values.";
    case "failed":
      return "We couldn't finish the upload.";
  }
}

function extractErrorMessage(err: unknown): string {
  // Axios error shape
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: unknown } }).response;
    const data = response?.data;
    if (typeof data === "string") return data;
    if (data && typeof data === "object") {
      // DRF validation: { files: ["message"] } or { detail: "..." } or { non_field_errors: [...] }
      for (const key of ["detail", "non_field_errors", "files"]) {
        const v = (data as Record<string, unknown>)[key];
        if (typeof v === "string") return v;
        if (Array.isArray(v) && v.length > 0 && typeof v[0] === "string") return v[0];
      }
      // Fall through: join all string values from the payload
      const allStrings: string[] = [];
      for (const v of Object.values(data as Record<string, unknown>)) {
        if (typeof v === "string") allStrings.push(v);
        else if (Array.isArray(v)) {
          for (const s of v) if (typeof s === "string") allStrings.push(s);
        }
      }
      if (allStrings.length > 0) return allStrings.join(" ");
    }
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}

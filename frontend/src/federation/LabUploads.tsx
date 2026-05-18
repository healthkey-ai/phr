import { injectStyles } from "./injectStyles";
injectStyles();
import { useState } from "react";
import { Loader2, Upload, Trash2, RotateCcw } from "lucide-react";

import { LabsProvider } from "./LabsProvider";
import { useLabsContext } from "./LabsContext";
import type { LabUploadsProps } from "./types";
import type { UploadJob } from "@/types/labs";
import {
  useLabUploads,
  useRetryExtraction,
  useDeleteLabUpload,
} from "./hooks";
import { LabUploadDialog } from "@/components/labs/LabUploadDialog";

function LabUploadsInner({
  onUploadComplete: _onUploadComplete,
  onResultsSaved: _onResultsSaved,
}: Pick<LabUploadsProps, "onUploadComplete" | "onResultsSaved">) {
  const { apiClient } = useLabsContext();
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: uploads = [], isLoading } = useLabUploads();
  const deleteUpload = useDeleteLabUpload();

  const inProgress = uploads.filter(
    (u) => u.status === "pending" || u.status === "processing",
  );
  const awaitingReview = uploads.filter(
    (u) => u.status === "completed",
  );
  const failed = uploads.filter((u) => u.status === "failed");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Lab Uploads</h2>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          <Upload className="h-4 w-4" />
          Upload Report
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading uploads...
        </div>
      )}

      {!isLoading && uploads.length === 0 && (
        <p className="text-sm text-gray-500">
          No uploads yet. Upload a lab report to get started.
        </p>
      )}

      {inProgress.length > 0 && (
        <UploadSection
          title="Processing"
          uploads={inProgress}
          onDelete={(id) => deleteUpload.mutate(id)}
          deletingId={deleteUpload.isPending ? deleteUpload.variables : undefined}
        />
      )}

      {awaitingReview.length > 0 && (
        <UploadSection
          title="Ready for review"
          uploads={awaitingReview}
          onDelete={(id) => deleteUpload.mutate(id)}
          deletingId={deleteUpload.isPending ? deleteUpload.variables : undefined}
        />
      )}

      {failed.length > 0 && (
        <UploadSection
          title="Failed"
          uploads={failed}
          onDelete={(id) => deleteUpload.mutate(id)}
          deletingId={deleteUpload.isPending ? deleteUpload.variables : undefined}
          showRetry
        />
      )}

      <LabUploadDialog open={dialogOpen} onOpenChange={setDialogOpen} apiClient={apiClient} />
    </div>
  );
}

function UploadSection({
  title,
  uploads,
  onDelete,
  deletingId,
  showRetry,
}: {
  title: string;
  uploads: UploadJob[];
  onDelete?: (id: number) => void;
  deletingId?: number;
  showRetry?: boolean;
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title} ({uploads.length})
      </h3>
      <ul className="space-y-2">
        {uploads.map((upload) => (
          <UploadItem
            key={upload.id}
            upload={upload}
            onDelete={onDelete}
            isDeleting={deletingId === upload.id}
            showRetry={showRetry}
          />
        ))}
      </ul>
    </div>
  );
}

function UploadItem({
  upload,
  onDelete,
  isDeleting,
  showRetry,
}: {
  upload: UploadJob;
  onDelete?: (id: number) => void;
  isDeleting?: boolean;
  showRetry?: boolean;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const retryExtraction = useRetryExtraction();

  const filenames =
    upload.files?.map((f) => f.original_filename).join(", ") || "Untitled";
  const date = new Date(upload.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const hasDetails =
    (upload.files?.length ?? 0) > 0 || (upload.parsed_results?.length ?? 0) > 0 || upload.error_message;

  return (
    <li className="rounded-md border border-gray-200 text-sm">
      <div className="flex items-center justify-between gap-3 px-3 py-2.5">
        <button
          type="button"
          onClick={() => hasDetails && setExpanded(!expanded)}
          className="min-w-0 flex-1 text-left"
        >
          <p className="truncate font-medium text-gray-900">{filenames}</p>
          <p className="text-xs text-gray-500">
            {date} · {statusLabel(upload.status)}
            {upload.parsed_results?.length > 0 &&
              ` · ${upload.parsed_results.length} results found`}
            {hasDetails && (
              <span className="ml-1">{expanded ? "▾" : "›"}</span>
            )}
          </p>
        </button>
        <div className="flex items-center gap-1.5">
          {upload.status === "processing" && (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          )}
        {showRetry && (
          <button
            type="button"
            onClick={() => retryExtraction.mutate(upload.id)}
            disabled={retryExtraction.isPending}
            className="rounded p-1 text-gray-400 hover:text-indigo-600 transition-colors"
            title="Retry extraction"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
        {onDelete && (
          confirmDelete ? (
            <span className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => { onDelete(upload.id); setConfirmDelete(false); }}
                disabled={isDeleting}
                className="text-xs text-red-600 hover:underline"
              >
                {isDeleting ? "Deleting..." : "Confirm"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="text-xs text-gray-500 hover:underline"
              >
                Cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="rounded p-1 text-gray-400 hover:text-red-600 transition-colors"
              title="Delete upload"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )
        )}
      </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 px-3 py-2.5 text-xs text-gray-600">
          {upload.files?.length > 0 && (
            <div className="mb-2">
              <p className="font-semibold text-gray-700 mb-1">Files</p>
              <ul className="space-y-0.5">
                {upload.files.map((f) => (
                  <li key={f.id} className="flex justify-between">
                    <span className="truncate">{f.original_filename}</span>
                    <span className="shrink-0 ml-2 text-gray-400">
                      {f.size_bytes >= 1024 * 1024
                        ? `${(f.size_bytes / (1024 * 1024)).toFixed(1)} MB`
                        : `${(f.size_bytes / 1024).toFixed(1)} KB`}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {upload.error_message && (
            <div className="mb-2">
              <p className="font-semibold text-red-600 mb-0.5">Error</p>
              <p className="text-red-600">{upload.error_message}</p>
            </div>
          )}

          {upload.parsed_results?.length > 0 && (
            <div>
              <p className="font-semibold text-gray-700 mb-1">
                Parsed results ({upload.parsed_results.length})
              </p>
              <table className="w-full text-left">
                <thead>
                  <tr className="text-gray-400">
                    <th className="pr-2 font-medium">Test</th>
                    <th className="pr-2 font-medium">Value</th>
                    <th className="pr-2 font-medium">Unit</th>
                    <th className="font-medium">Match</th>
                  </tr>
                </thead>
                <tbody>
                  {upload.parsed_results.map((row) => (
                    <tr key={row.source_index}>
                      <td className="pr-2 truncate max-w-[120px]" title={row.raw_name}>
                        {row.matched_test_name || row.raw_name}
                      </td>
                      <td className="pr-2 font-mono">{row.value ?? "—"}</td>
                      <td className="pr-2">{row.unit || "—"}</td>
                      <td className="text-gray-400">{row.match_method}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!upload.files?.length && !upload.parsed_results?.length && !upload.error_message && (
            <p className="text-gray-400">No details available.</p>
          )}
        </div>
      )}
    </li>
  );
}

function statusLabel(status: string): string {
  switch (status) {
    case "pending": return "Queued";
    case "processing": return "Processing";
    case "completed": return "Ready for review";
    case "failed": return "Failed";
    default: return status;
  }
}

export function LabUploads({
  apiClient,
  apiBasePath,
  queryClient,
  className,
  theme,
  onUploadComplete,
  onResultsSaved,
}: LabUploadsProps) {
  return (
    <LabsProvider
      apiClient={apiClient}
      apiBasePath={apiBasePath}
      queryClient={queryClient}
      theme={theme}
      className={className}
    >
      <LabUploadsInner
        onUploadComplete={onUploadComplete}
        onResultsSaved={onResultsSaved}
      />
    </LabsProvider>
  );
}

export default LabUploads;

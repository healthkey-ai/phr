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
        <UploadSection title="Processing" uploads={inProgress} />
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
  const retryExtraction = useRetryExtraction();

  const filenames =
    upload.files?.map((f) => f.original_filename).join(", ") || "Untitled";
  const date = new Date(upload.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <li className="flex items-center justify-between gap-3 rounded-md border border-gray-200 px-3 py-2.5 text-sm">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-gray-900">{filenames}</p>
        <p className="text-xs text-gray-500">
          {date} · {statusLabel(upload.status)}
          {upload.parsed_results?.length > 0 &&
            ` · ${upload.parsed_results.length} results found`}
        </p>
        {upload.error_message && (
          <p className="mt-1 text-xs text-red-600">{upload.error_message}</p>
        )}
      </div>
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

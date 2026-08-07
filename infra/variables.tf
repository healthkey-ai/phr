variable "render_api_key" {
  description = "Render API key (or set RENDER_API_KEY in the environment)."
  type        = string
  sensitive   = true
  default     = null
}

variable "owner_id" {
  description = "Render workspace/team id that owns the resources."
  type        = string
  default     = "tea-d5sfrln18n1s739ntca0" # My Workspace
}

variable "environment_id" {
  description = "Render project environment the resources belong to (project prj-d7fvvilckfvc73b80rgg / HealthKey Patient App)."
  type        = string
  default     = "evm-d7fvvilckfvc73b80rh0" # staging
}

variable "region" {
  description = "Render region for all resources."
  type        = string
  default     = "oregon"
}

variable "deploy_branch" {
  description = "Git branch auto-deployed to this environment."
  type        = string
  default     = "dev"
}

variable "cors_allowed_origins" {
  description = "Comma-separated extra origins allowed by CORS (SPA is same-origin, so usually empty)."
  type        = string
  default     = ""
}

variable "promop_remote_url" {
  description = "Origin serving promop's federation remote (remoteEntry.js under /remote/)."
  type        = string
  default     = "https://promop-staging.onrender.com/remote"
}

variable "promop_api_url" {
  description = "promop API base used by the federated PatientInfo component."
  type        = string
  default     = "https://promop-staging.onrender.com/api"
}

# ── LABS ───────────────────────────────────────────────────────────────────

variable "labs_deploy_branch" {
  description = "Git branch the labs services deploy from."
  type        = string
  default     = "dev"
}

variable "labs_upload_enabled" {
  description = <<-EOT
    Gates POST /api/v1/labs/uploads/. Requires object storage: Render disks
    are per-service, so a PDF the web service writes locally is invisible to
    the worker that has to rasterise it, and every upload would be accepted
    and then fail in extraction.
  EOT
  type        = bool
  default     = true
}

variable "labs_url" {
  description = <<-EOT
    Public URL of the labs service, baked into phr's SPA at build time.
    Pinned rather than referenced: labs reads phr's URL for PHR_BASE_URL and
    CORS, so a direct reference back would be a dependency cycle. Update it
    if the labs service is ever recreated.
  EOT
  type        = string
  default     = "https://labs-oy0f.onrender.com"
}

variable "labs_gcs_bucket" {
  description = <<-EOT
    Bucket holding uploaded lab reports. Shared with the GCP deployment for
    now — object names are UUIDs and each deployment only references its own
    rows, so the two do not collide.
  EOT
  type        = string
  default     = "hk-labs-staging-uploads"
}

variable "labs_gcs_project_id" {
  description = "GCP project owning labs_gcs_bucket."
  type        = string
  default     = "ht-phr"
}

variable "labs_gcs_credentials_json" {
  description = <<-EOT
    Service-account key JSON for the bucket. Render cannot use workload
    identity, so it needs a downloadable credential; the account behind it
    should hold object access to this one bucket and nothing else. Supply
    via TF_VAR_labs_gcs_credentials_json — never commit it.
  EOT
  type        = string
  sensitive   = true
  default     = ""
}

variable "labs_loinc_min_confidence" {
  description = <<-EOT
    Lowest self-reported extractor confidence whose LOINC code is worth
    checking ("high" or "medium"). The code still has to survive the name,
    specimen, unit-family and value-type gates either way — this only decides
    which claims are examined at all.

    Currently "medium", being trialled on staging. Revert to "high" if it
    admits codes the other gates let through wrongly.
  EOT
  type        = string
  default     = "medium"
}

variable "anthropic_api_key" {
  description = "Claude vision key for lab report extraction. Supply via TF_VAR_anthropic_api_key."
  type        = string
  sensitive   = true
  default     = ""
}

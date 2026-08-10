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

variable "soc_deploy_branch" {
  description = "Git branch the soc service deploys from."
  type        = string
  default     = "main"
}

variable "soc_url" {
  description = <<-EOT
    Public URL of the soc service, baked into the portal's SPA at build
    time. Pinned rather than referenced for the same reason as labs_url:
    soc reads the portal's URL for PHR_BASE_URL and CORS, so referencing it
    back would be a dependency cycle.
  EOT
  type        = string
  default     = "https://soc-o2zz.onrender.com"
}

# ── EXACT ──────────────────────────────────────────────────────────────────

variable "exact_environment_id" {
  description = <<-EOT
    Render environment the exact staging resources live in. Unlike LABS and
    SOC, the EXACT project is not created here: it already existed, holding a
    Production environment and the exact-2 service that another team owns.
    This points at a `staging` environment added alongside that one, so
    Terraform manages the staging resources without taking their production
    into its state.
  EOT
  type        = string
  default     = "evm-d9t2tqrncjis73brting" # EXACT / staging
}

variable "exact_deploy_branch" {
  description = "Git branch the exact service deploys from."
  type        = string
  default     = "main"
}

variable "exact_url" {
  description = <<-EOT
    Public URL of the exact service, baked into the portal's SPA at build
    time. Pinned rather than referenced for the same reason as labs_url and
    soc_url: exact reads the portal's URL for PHR_BASE_URL and CORS, so
    referencing it back would be a dependency cycle.

    Empty leaves the Find Trials menu item disabled rather than pointing it
    at nothing.
  EOT
  type        = string
  default     = "https://exact-ybht.onrender.com"
}

variable "exact_trials_database_url" {
  description = <<-EOT
    Postgres URL for the trials data (schema `trials_*`), read by exact's
    database router. Not a Render database: the trial corpus lives in an
    externally managed Postgres that both this deployment and the existing
    exact instance read, so staging shares it rather than holding a stale
    copy of ~271 MB that nothing refreshes.

    Shared, so treat it as read-only from here. NEVER set
    TRIALS_DATABASE_INIT_FROM_BACKUP alongside this value — that switch
    makes the container DROP the public schema before restoring a snapshot,
    which against a shared database destroys the corpus for every reader.
    Give staging its own database first if you ever want that path.

    Supply via TF_VAR_exact_trials_database_url — it carries credentials and
    must never be committed. Left empty, exact falls back to single-database
    mode and serves no trials at all.
  EOT
  type        = string
  sensitive   = true
  default     = ""
}

variable "exact_ctomop_service_token" {
  description = <<-EOT
    Bearer token exact presents to promop when resolving `?person_id=`
    server-side. The portal's Find Trials page does not use that path — it
    reads the record in the browser with the patient's own token and posts
    the row inline — so this stays empty until something needs the resolver.

    Worth knowing before enabling it: that endpoint does not bind person_id
    to the requesting user, so a service token here would let any caller of
    exact read any patient's record. Supply via
    TF_VAR_exact_ctomop_service_token.
  EOT
  type        = string
  sensitive   = true
  default     = ""
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

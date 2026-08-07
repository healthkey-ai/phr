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
    Gates POST /api/v1/labs/uploads/. Keep false until object storage is
    configured: Render disks are per-service, so a PDF the web service
    writes locally is invisible to the worker that has to rasterise it —
    every upload would be accepted and then fail in extraction.
  EOT
  type        = bool
  default     = false
}

variable "anthropic_api_key" {
  description = "Claude vision key for lab report extraction. Empty until uploads are enabled."
  type        = string
  sensitive   = true
  default     = ""
}

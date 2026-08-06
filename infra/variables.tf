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

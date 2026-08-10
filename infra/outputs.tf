output "backend_url" {
  description = "Public URL of the phr service (API + SPA)."
  value       = render_web_service.backend.url
}

output "backend_service_id" {
  value = render_web_service.backend.id
}

output "postgres_id" {
  value = render_postgres.db.id
}

output "jwks_url" {
  description = "JWKS endpoint sibling services use to verify phr-issued tokens."
  value       = "${render_web_service.backend.url}/api/v1/auth/jwks/"
}

output "labs_url" {
  description = "Public URL of the labs service (API + federation remote under /static/)."
  value       = render_web_service.labs.url
}

output "labs_remote_url" {
  description = "Value for phr's VITE_LABS_REMOTE_URL build arg."
  value       = "${render_web_service.labs.url}/static"
}

output "labs_api_url" {
  description = "Value for phr's VITE_LABS_API_URL build arg."
  value       = "${render_web_service.labs.url}/api/v1"
}

output "soc_url" {
  description = "Public URL of the soc service (API + federation remote at /remoteEntry.js)."
  value       = render_web_service.soc.url
}

output "soc_remote_url" {
  description = "Value for the portal's VITE_SOC_REMOTE_URL build arg (set soc_url to this)."
  value       = render_web_service.soc.url
}

output "exact_url" {
  description = "Public URL of the exact service (API + federation remote at /remoteEntry.js)."
  value       = render_web_service.exact.url
}

output "exact_remote_url" {
  description = "Value for the portal's VITE_EXACT_REMOTE_URL build arg (set exact_url to this)."
  value       = render_web_service.exact.url
}

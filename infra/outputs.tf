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

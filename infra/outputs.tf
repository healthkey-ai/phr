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

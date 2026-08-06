terraform {
  required_version = ">= 1.5"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = "~> 1.3"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Auth: export RENDER_API_KEY (and RENDER_OWNER_ID, or set the variables).
provider "render" {
  api_key  = var.render_api_key
  owner_id = var.owner_id
}

# ── Secrets generated and held in Terraform state (local, gitignored) ───────

resource "random_password" "django_secret_key" {
  length  = 50
  special = false
}

# phr is the identity provider for the service family: RS256 keypair signs
# JWTs; sibling services verify offline via GET /api/v1/auth/jwks/.
resource "tls_private_key" "jwt" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

# ── Database — the identity DB for the HealthKey service family ─────────────

resource "render_postgres" "db" {
  name           = "phr-db"
  plan           = "basic_256mb"
  region         = var.region
  version        = "16"
  database_name  = "phr"
  database_user  = "phr"
  environment_id = var.environment_id
}

# ── Web service — single container: Django API + built SPA ──────────────────

resource "render_web_service" "backend" {
  name           = "phr"
  plan           = "starter"
  region         = var.region
  environment_id = var.environment_id

  runtime_source = {
    docker = {
      repo_url        = "https://github.com/healthkey-ai/phr"
      branch          = var.deploy_branch
      dockerfile_path = "./Dockerfile"
      context         = "."
      auto_deploy     = true
    }
  }

  health_check_path = "/api/v1/health/"

  # Runs once per deploy before traffic switches — without it the database
  # never gets migrated and every ORM endpoint 500s while health/JWKS
  # (no-DB) stay green.
  pre_deploy_command = "python manage.py migrate --noinput"

  env_vars = {
    DJANGO_SETTINGS_MODULE = { value = "config.settings.production" }
    DEBUG                  = { value = "False" }
    SECRET_KEY             = { value = random_password.django_secret_key.result }
    ALLOWED_HOSTS          = { value = "localhost,127.0.0.1,.onrender.com" }
    DATABASE_URL           = { value = render_postgres.db.connection_info.internal_connection_string }

    # JWT — phr is the token issuer for the whole service family.
    JWT_ISSUER                  = { value = "healthkey-phr" }
    JWT_ACCESS_LIFETIME_MINUTES = { value = "15" }
    JWT_REFRESH_LIFETIME_DAYS   = { value = "7" }
    JWT_PRIVATE_KEY             = { value = tls_private_key.jwt.private_key_pem }
    JWT_PUBLIC_KEY              = { value = tls_private_key.jwt.public_key_pem }

    # Same-origin SPA; CORS list stays empty unless another origin needs in.
    CORS_ALLOWED_ORIGINS = { value = var.cors_allowed_origins }
  }
}

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
      # Deploys are driven by the deploy-staging GitHub workflow after CI
      # passes — Render must not race it with its own push-triggered deploy.
      auto_deploy = false
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

    # Federated-remote origins — consumed at Docker BUILD time (the
    # Dockerfile declares matching ARGs) and baked into the SPA bundle.
    # Changing these needs a rebuild, not just a restart.
    VITE_PROMOP_REMOTE_URL = { value = var.promop_remote_url }
    VITE_PROMOP_API_URL    = { value = var.promop_api_url }

    # A variable, not render_web_service.labs.url: labs reads phr's URL for
    # PHR_BASE_URL and CORS, so referencing it back here is a dependency
    # cycle. This is the safer side to pin — a stale labs URL breaks the
    # federated uploads page, while a stale phr URL in labs would fail every
    # token verification and take the whole service down.
    VITE_LABS_REMOTE_URL = { value = "${var.labs_url}/static" }
    VITE_LABS_API_URL    = { value = "${var.labs_url}/api/v1" }
  }
}

# ── LABS — lab report uploads + extraction ──────────────────────────────────
#
# Its own Render project: labs owns its database and broker, and talks to phr
# only over the public API (token verification via JWKS), so nothing here
# needs to share an environment with phr.
#
# Two services off one image. The web service answers the API and serves the
# federation remote at /static/remoteEntry.js; the worker runs extraction,
# which takes 30-120s against a vision model and cannot live in a request.
# They share the database and the broker, and nothing else — see
# labs_upload_enabled for why that matters.

resource "render_project" "labs" {
  name = "LABS"
  environments = {
    staging = {
      name             = "staging"
      protected_status = "unprotected"
      # Only the browser and phr reach these services, both over the public
      # API, so nothing here needs to accept traffic from other environments.
      network_isolated = true
    }
  }
}

locals {
  labs_environment_id = render_project.labs.environments["staging"].id
}

resource "random_password" "labs_secret_key" {
  length  = 50
  special = false
}

resource "render_postgres" "labs_db" {
  name           = "labs-db"
  plan           = "basic_256mb"
  region         = var.region
  version        = "16"
  database_name  = "hk_labs"
  database_user  = "hk_labs"
  environment_id = local.labs_environment_id
}

resource "render_keyvalue" "labs_broker" {
  name           = "labs-broker"
  plan           = "starter"
  region         = var.region
  environment_id = local.labs_environment_id
  # Queued extraction jobs are work we cannot reconstruct, so never evict
  # to reclaim memory — fail the enqueue loudly instead.
  max_memory_policy = "noeviction"
}

locals {
  labs_repo = "https://github.com/healthkey-ai/hk-labs"

  # Both labs services run the same Django app and need identical settings;
  # only the start command differs.
  labs_env_vars = {
    DJANGO_SETTINGS_MODULE = { value = "config.settings.production" }
    DEBUG                  = { value = "False" }
    SECRET_KEY             = { value = random_password.labs_secret_key.result }
    ALLOWED_HOSTS          = { value = "localhost,127.0.0.1,.onrender.com" }
    DATABASE_URL           = { value = render_postgres.labs_db.connection_info.internal_connection_string }

    CELERY_BROKER_URL     = { value = "${render_keyvalue.labs_broker.connection_info.internal_connection_string}/0" }
    CELERY_RESULT_BACKEND = { value = "${render_keyvalue.labs_broker.connection_info.internal_connection_string}/1" }

    # phr issues the tokens labs verifies; PhrTokenProvider derives the
    # JWKS and introspection URLs from this base.
    PHR_BASE_URL = { value = render_web_service.backend.url }
    PHR_ISSUER   = { value = "healthkey-phr" }

    # The browser calls this API from the phr origin, so phr must be allowed
    # through CORS. The federation remote is served by whitenoise, which
    # already sets Access-Control-Allow-Origin for static files.
    CORS_ALLOWED_ORIGINS = { value = render_web_service.backend.url }

    # Object storage, not a Render disk: disks attach to a single service, so
    # a PDF the web service wrote would be invisible to the worker that has
    # to rasterise it. Both services address the same bucket instead.
    GS_BUCKET_NAME      = { value = var.labs_gcs_bucket }
    GS_PROJECT_ID       = { value = var.labs_gcs_project_id }
    GS_CREDENTIALS_JSON = { value = var.labs_gcs_credentials_json }

    LAB_UPLOAD_ENABLED = { value = tostring(var.labs_upload_enabled) }
    LAB_LLM_PROVIDER   = { value = "claude" }
    ANTHROPIC_API_KEY  = { value = var.anthropic_api_key }
  }
}

resource "render_web_service" "labs" {
  name           = "labs"
  plan           = "starter"
  region         = var.region
  environment_id = local.labs_environment_id

  runtime_source = {
    docker = {
      repo_url        = local.labs_repo
      branch          = var.labs_deploy_branch
      dockerfile_path = "./Dockerfile"
      context         = "."
      auto_deploy     = false
    }
  }

  health_check_path = "/api/v1/health/"

  # The health check queries the database, so it fails until migrations run.
  pre_deploy_command = "python manage.py migrate --noinput"

  env_vars = local.labs_env_vars
}

resource "render_background_worker" "labs_worker" {
  name           = "labs-worker"
  plan           = "starter"
  region         = var.region
  environment_id = local.labs_environment_id

  runtime_source = {
    docker = {
      repo_url        = local.labs_repo
      branch          = var.labs_deploy_branch
      dockerfile_path = "./Dockerfile"
      context         = "."
      auto_deploy     = false
    }
  }

  start_command = "celery -A config worker --loglevel=info --concurrency=2 --max-tasks-per-child=100 --without-gossip --without-mingle"

  env_vars = local.labs_env_vars
}

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

    # soc serves its remote from the site root, not under a static prefix.
    # Empty until soc is deployed and soc_url is set, which leaves the Find
    # Treatments menu item disabled rather than pointing it at nothing.
    VITE_SOC_REMOTE_URL = { value = var.soc_url }
    # Origin only — soc's remote appends its own /api/v1 path.
    VITE_SOC_API_URL = { value = var.soc_url }

    # exact serves its remote from the site root too (whitenoise at "/"),
    # and its API client is origin-only — the remote builds its own paths.
    VITE_EXACT_REMOTE_URL = { value = var.exact_url }
    VITE_EXACT_API_URL    = { value = var.exact_url }
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

    # Committed results are written to promop, which is where phr's Lab
    # Results page reads them from — the same promop the SPA is pointed at,
    # or saved values land in the labs database and never surface anywhere.
    # No service token: sync forwards the patient's own bearer token.
    CTOMOP_SYNC_URL = { value = "${var.promop_api_url}/lab-results/sync/" }

    # Object storage, not a Render disk: disks attach to a single service, so
    # a PDF the web service wrote would be invisible to the worker that has
    # to rasterise it. Both services address the same bucket instead.
    GS_BUCKET_NAME      = { value = var.labs_gcs_bucket }
    GS_PROJECT_ID       = { value = var.labs_gcs_project_id }
    GS_CREDENTIALS_JSON = { value = var.labs_gcs_credentials_json }

    LAB_UPLOAD_ENABLED       = { value = tostring(var.labs_upload_enabled) }
    LAB_LOINC_MIN_CONFIDENCE = { value = var.labs_loinc_min_confidence }
    LAB_LLM_PROVIDER         = { value = "claude" }
    ANTHROPIC_API_KEY        = { value = var.anthropic_api_key }
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

  lifecycle {
    # These two live in state and nowhere else in the repo — their variables
    # default to "" so that nothing secret is committed. That default is the
    # danger: an apply run without TF_VAR_anthropic_api_key or
    # TF_VAR_labs_gcs_credentials_json exported reads "" as the intended
    # value and quietly nulls them, which takes out lab extraction and every
    # upload while the service still reports healthy. It has come close
    # twice.
    #
    # The trade: Terraform can no longer change these once set. Rotate them
    # in the Render dashboard, or remove the entry here for the one apply
    # that rotates it. Worth it — a rotation is a deliberate act someone is
    # watching, an accidental wipe is not.
    ignore_changes = [
      env_vars["ANTHROPIC_API_KEY"],
      env_vars["GS_CREDENTIALS_JSON"],
    ]
  }
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

  lifecycle {
    # Same reasoning as the web service above, and it matters more here: the
    # worker is the half that actually calls the vision model and reads the
    # bucket, so a wipe here fails extraction in the background where no
    # request surfaces it.
    ignore_changes = [
      env_vars["ANTHROPIC_API_KEY"],
      env_vars["GS_CREDENTIALS_JSON"],
    ]
  }
}

# ── SOC — treatment recommendations (Find Treatments) ───────────────────────
#
# One web service and a database. No broker: the recommend pipeline answers
# in the request, and nothing runs on a schedule yet — add a worker when
# something actually needs one.

resource "render_project" "soc" {
  name = "SOC"
  environments = {
    staging = {
      name             = "staging"
      protected_status = "unprotected"
      network_isolated = true
    }
  }
}

locals {
  soc_environment_id = render_project.soc.environments["staging"].id
}

resource "random_password" "soc_secret_key" {
  length  = 50
  special = false
}

resource "render_postgres" "soc_db" {
  name           = "soc-db"
  plan           = "basic_256mb"
  region         = var.region
  version        = "16"
  database_name  = "soc"
  database_user  = "soc"
  environment_id = local.soc_environment_id
}

resource "render_web_service" "soc" {
  name           = "soc"
  plan           = "starter"
  region         = var.region
  environment_id = local.soc_environment_id

  runtime_source = {
    docker = {
      repo_url        = "https://github.com/healthkey-ai/soc"
      branch          = var.soc_deploy_branch
      dockerfile_path = "./Dockerfile"
      context         = "."
      auto_deploy     = false
    }
  }

  health_check_path  = "/healthz"
  pre_deploy_command = "python manage.py migrate --noinput"

  env_vars = {
    DJANGO_ENV = { value = "staging" }
    SECRET_KEY = { value = random_password.soc_secret_key.result }
    # staging settings raise at import if this is unset, so the service would
    # crash-loop rather than start with a permissive default.
    ALLOWED_HOSTS = { value = ".onrender.com" }
    DATABASE_URL  = { value = render_postgres.soc_db.connection_info.internal_connection_string }

    # The portal issues the tokens soc verifies; its provider derives the
    # JWKS and introspection URLs from this base. It is the only identity
    # provider here — there is no Firebase on Render, and listing a provider
    # that cannot work only logs "no credentials configured" per request.
    PARTNER_AUTH_PROVIDERS = { value = "accounts.providers.phr.PhrTokenProvider" }
    PHR_BASE_URL           = { value = render_web_service.backend.url }
    PHR_ISSUER             = { value = "healthkey-phr" }

    # The browser calls this API from the portal's origin. The remote itself
    # is served by whitenoise, which already answers cross-origin.
    CORS_ALLOWED_ORIGINS = { value = render_web_service.backend.url }
  }
}

# ── EXACT — clinical trial matching (Find Trials) ───────────────────────────
#
# One web service and a database, same shape as SOC — but unlike LABS and SOC
# this does NOT create its own project. An EXACT project already exists and
# holds someone else's Production environment (the `exact-2` service and its
# database). Terraform therefore owns only the resources inside a `staging`
# environment created alongside it, addressed by id through
# exact_environment_id, exactly as phr's own service is.
#
# Importing that project to manage both environments from here was the
# alternative and was rejected: it would put another team's production
# environment inside this state file, one `terraform destroy` away from
# deletion, to gain nothing staging needs.
#
# Three databases, and only one of them is provisioned here:
#   default  — this service's own Django tables (auth, sessions, identities).
#   trials   — the trial corpus, an externally managed Postgres shared with
#              the existing exact instance. See exact_trials_database_url.
#   promop   — not a database connection at all. Patient records reach exact
#              over HTTP: the portal reads them in the browser with the
#              patient's own token and posts the row to /normalize-ctomop-row/.
#              CTOMOP_BASE below only serves exact's server-side `?person_id=`
#              resolver, which the portal does not use.

resource "random_password" "exact_secret_key" {
  length  = 50
  special = false
}

resource "render_postgres" "exact_db" {
  name           = "exact-db"
  plan           = "basic_256mb"
  region         = var.region
  version        = "16"
  database_name  = "exact"
  database_user  = "exact"
  environment_id = var.exact_environment_id
}

resource "render_web_service" "exact" {
  name           = "exact"
  plan           = "starter"
  region         = var.region
  environment_id = var.exact_environment_id

  runtime_source = {
    docker = {
      repo_url        = "https://github.com/healthkey-ai/exact"
      branch          = var.exact_deploy_branch
      dockerfile_path = "./Dockerfile"
      context         = "."
      auto_deploy     = false
    }
  }

  health_check_path = "/healthz"

  # No separate PostGIS step: the GeoDjango backend's prepare_database()
  # issues CREATE EXTENSION IF NOT EXISTS postgis itself, and migrate calls
  # it. An earlier attempt ran psql here first and failed — Render does not
  # expand $DATABASE_URL in the pre-deploy command, so psql fell through to a
  # local socket that does not exist.
  #
  # --run-syncdb matches the container entrypoint, which is what has always
  # created tables for the apps that carry no migrations.
  pre_deploy_command = "python manage.py migrate --run-syncdb --noinput"

  env_vars = {
    ENVIRONMENT = { value = "staging" }
    DEBUG       = { value = "False" }
    # settings.py raises at import when this is unset outside local/DEBUG,
    # so the service crash-loops rather than booting on a shared default.
    SECRET_KEY    = { value = random_password.exact_secret_key.result }
    ALLOWED_HOSTS = { value = "localhost,127.0.0.1,.onrender.com" }
    DATABASE_URL  = { value = render_postgres.exact_db.connection_info.internal_connection_string }

    # Shared, externally managed corpus — read-only from here. See the
    # variable's own warning about TRIALS_DATABASE_INIT_FROM_BACKUP, which is
    # deliberately left unset: it drops the public schema before restoring.
    TRIALS_DATABASE_URL = { value = var.exact_trials_database_url }

    # The entrypoint migrates on every boot by default; pre_deploy_command
    # already did it, before traffic switched rather than after.
    RUN_MIGRATIONS = { value = "false" }

    # The portal issues the tokens exact verifies. Only provider configured:
    # there is no Firebase on Render, and naming one that cannot work costs a
    # "no credentials configured" log line on every request.
    PARTNER_AUTH_PROVIDERS = { value = "accounts.providers.phr.PhrTokenProvider" }
    PHR_BASE_URL           = { value = render_web_service.backend.url }
    PHR_ISSUER             = { value = "healthkey-phr" }

    # The browser calls this API from the portal's origin. The remote itself
    # is served by CorsWhiteNoiseMiddleware, which answers cross-origin.
    CORS_ALLOWED_ORIGINS = { value = render_web_service.backend.url }

    # The same promop the portal reads from — derived from promop_api_url so
    # the two cannot drift. Origin only: the client appends
    # /api/patient-info/<id>/ itself.
    CTOMOP_BASE          = { value = trimsuffix(var.promop_api_url, "/api") }
    CTOMOP_SERVICE_TOKEN = { value = var.exact_ctomop_service_token }
  }

  lifecycle {
    # Same trap as the labs services: the variable defaults to "" so no
    # credential is committed, and an apply without
    # TF_VAR_exact_trials_database_url exported would read that "" as intent
    # and null it. exact then falls back to single-database mode and serves
    # zero trials — from a service that still passes its health check, since
    # /healthz deliberately does not probe this alias.
    #
    # CTOMOP_SERVICE_TOKEN is left out on purpose: it is empty by design, so
    # there is nothing to protect, and ignoring it would silently swallow the
    # apply that first sets it.
    ignore_changes = [
      env_vars["TRIALS_DATABASE_URL"],
    ]
  }
}

# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build

# Federated-remote origins are baked into the bundle at build time. Render
# passes service env vars into Docker builds for ARG-declared names — set
# these on the service (infra/main.tf) or the SPA falls back to localhost
# defaults and the federated pages can't load their modules.
ARG VITE_PROMOP_REMOTE_URL
ARG VITE_PROMOP_API_URL
ARG VITE_SOC_REMOTE_URL
ARG VITE_SOC_API_URL
ARG VITE_LABS_REMOTE_URL
ARG VITE_LABS_API_URL
ARG VITE_EXACT_REMOTE_URL
ARG VITE_EXACT_API_URL
ENV VITE_PROMOP_REMOTE_URL=$VITE_PROMOP_REMOTE_URL \
    VITE_PROMOP_API_URL=$VITE_PROMOP_API_URL \
    VITE_SOC_REMOTE_URL=$VITE_SOC_REMOTE_URL \
    VITE_SOC_API_URL=$VITE_SOC_API_URL \
    VITE_LABS_REMOTE_URL=$VITE_LABS_REMOTE_URL \
    VITE_LABS_API_URL=$VITE_LABS_API_URL \
    VITE_EXACT_REMOTE_URL=$VITE_EXACT_REMOTE_URL \
    VITE_EXACT_API_URL=$VITE_EXACT_API_URL

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Copy frontend build into Django's staticfiles source
COPY --from=frontend-build /app/frontend/dist ./frontend_dist

RUN python manage.py collectstatic --noinput

RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8080

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120"]

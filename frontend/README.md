# HealthKey Frontend

Vite + React 18 + TypeScript + Tailwind + shadcn/ui + React Query.

## Quick start

```bash
npm install
npm run dev
```

App will be live at http://localhost:5173/ — proxies `/api` to http://localhost:8000 by default.

## Environment variables

All variables have working defaults, so you can run dev with no `.env` file.
To customize, copy `.env.example` to `.env` (or `.env.local` for per-developer
overrides — gitignored).

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `/api/v1` | Axios baseURL for backend API. Use a relative path in dev (proxied), absolute URL in production (`https://api.healthkey.io/api/v1`) |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Dev-only: where the Vite proxy forwards `/api/*` requests. Not bundled into production builds |

For production builds, create `.env.production` with the absolute API URL:

```
VITE_API_URL=https://api.healthkey.io/api/v1
```

Then `npm run build` will inline that value into the bundle.

## Build

```bash
npm run build
npm run preview
```

## Stack

- **Framework:** React 18 + Vite
- **Routing:** React Router 6
- **Server state:** TanStack Query (React Query) v5
- **Forms:** React Hook Form + Zod
- **Styling:** Tailwind CSS 3 + shadcn/ui + Radix UI
- **Icons:** Lucide React
- **Auth:** JWT in memory + axios interceptors

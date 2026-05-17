# Module Federation Plan: Labs Feature

## Context

The HealthKey PHR frontend needs to expose its Labs functionality as a federated module consumable by other React apps. Currently the app is a monolithic Vite SPA with no micro-frontend infrastructure. The goal is to extract labs components into a Module Federation remote that exposes multiple entry points — host apps pick which components to render, composing their own UI.

## Architecture Decision

- **Plugin**: `@module-federation/vite` (Vite-native, supports Vite 8)
- **Auth contract**: Firebase token exchange — see [Cross-App Authentication](#cross-app-authentication) below
- **Shared deps**: `react`, `react-dom`, `@tanstack/react-query`, `axios` (singleton)
- **CSS isolation**: Tailwind with `prefix: "hk-"` + `important: '.hk-labs-root'` scoping
- **Structure**: Same repo, existing app becomes both host and remote

## Cross-App Authentication

### Problem

The two apps use different auth systems with no overlap:

| | **ht-phr** (host app) | **phr** (labs module backend) |
|---|---|---|
| Auth provider | Firebase Auth | Django SimpleJWT |
| Token type | Firebase ID token | Django-issued JWT |
| Backend verification | Firebase Admin SDK (`firebase-admin`) | Django's own signing key |
| User model | `User` with `firebase_uid` field | standalone `User` |
| Token storage | In-memory (Firebase SDK manages refresh) | Access in-memory, refresh in localStorage |

A Firebase ID token from the host app is meaningless to the PHR backend — different signing keys, different user tables. The federated module talks directly to the PHR backend, so it needs a PHR JWT.

### Solution: Firebase Token Exchange

Add a single endpoint to the PHR backend that accepts a Firebase ID token, verifies it against the same Firebase project the host app uses, and returns a PHR JWT for the corresponding user (auto-provisioning if needed).

```
┌──────────────┐     Firebase ID token      ┌──────────────────┐
│   ht-phr     │ ──────────────────────────► │  PHR backend     │
│  (host app)  │  POST /auth/partner-token/  │                  │
│              │ ◄────────────────────────── │  1. verify with  │
│              │     { access, refresh }      │     firebase-admin│
│              │                              │  2. find/create  │
│              │                              │     local User   │
│              │                              │  3. issue PHR JWT│
└──────┬───────┘                              └──────────────────┘
       │
       │  Creates axios instance with PHR JWT
       │
       ▼
┌──────────────┐
│ Labs Module  │  All API calls use PHR JWT
│ (federated)  │  → /api/v1/labs/*
└──────────────┘
```

**Why this works:**
1. The host app (`ht-phr`) already uses Firebase Auth with `firebase-admin` SDK — the PHR backend can verify the exact same tokens using the same Firebase project credentials.
2. The host's User model already has a `phr_person_id` field — designed for cross-system linking.
3. No proxy needed — the module talks directly to the PHR backend with a real PHR JWT.
4. The module stays auth-agnostic — it just receives an authenticated axios instance.
5. Single new endpoint on the PHR backend, ~40 lines of code.

### Backend Changes (PHR)

**New dependencies:**
- `firebase-admin` in `requirements.txt`
- Firebase service account JSON (same credentials as ht-phr, shared via env var `GOOGLE_APPLICATION_CREDENTIALS` or `FIREBASE_CREDENTIALS_JSON`)

**New field on PHR User model:**
```python
# backend/apps/accounts/models.py
firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)
```

**New endpoint — `POST /api/v1/auth/partner-token/`:**
```python
# backend/apps/accounts/views.py

class PartnerTokenView(APIView):
    """Exchange a Firebase ID token for PHR JWT credentials.

    Called by host apps before mounting the federated labs module.
    Verifies the Firebase token, finds or creates a linked PHR user,
    and returns a PHR access + refresh token pair.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        firebase_token = request.data.get("firebase_token", "")
        if not firebase_token:
            return Response({"detail": "firebase_token required"}, status=400)

        # 1. Verify against the same Firebase project
        try:
            decoded = firebase_admin.auth.verify_id_token(firebase_token)
        except Exception:
            return Response({"detail": "Invalid Firebase token"}, status=401)

        uid = decoded["uid"]
        email = decoded.get("email", "")

        # 2. Find or create a local PHR user linked by firebase_uid
        user, created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={"email": email, "username": uid},
        )
        if created:
            logger.info("partner_token: provisioned new PHR user %d for firebase_uid=%s", user.pk, uid)

        # 3. Issue PHR JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user.pk,
            "created": created,
        })
```

**URL registration:**
```python
# backend/apps/accounts/urls.py
path("partner-token/", PartnerTokenView.as_view(), name="partner-token"),
```

### Host App Integration (ht-phr)

When mounting the labs module, the host exchanges its Firebase token for a PHR JWT and creates a dedicated axios instance:

```typescript
// ht-phr/frontend/src/lib/phr-client.ts
import { auth } from '@/lib/firebase';
import axios from 'axios';

const PHR_API_BASE = import.meta.env.VITE_PHR_API_URL || 'http://localhost:9000/api/v1';

let phrTokens: { access: string; refresh: string } | null = null;

export async function getPhrApiClient() {
  const firebaseUser = auth.currentUser;
  if (!firebaseUser) throw new Error('Not authenticated');

  // Exchange Firebase token for PHR JWT (cache until refresh needed)
  if (!phrTokens) {
    const idToken = await firebaseUser.getIdToken();
    const res = await axios.post(`${PHR_API_BASE}/auth/partner-token/`, {
      firebase_token: idToken,
    });
    phrTokens = { access: res.data.access, refresh: res.data.refresh };
  }

  const client = axios.create({
    baseURL: PHR_API_BASE,
    headers: { Authorization: `Bearer ${phrTokens.access}` },
  });

  // Auto-refresh on 401
  client.interceptors.response.use(
    (r) => r,
    async (err) => {
      if (err.response?.status === 401 && !err.config._retry) {
        err.config._retry = true;
        const refreshRes = await axios.post(`${PHR_API_BASE}/auth/token/refresh/`, {
          refresh: phrTokens!.refresh,
        });
        phrTokens!.access = refreshRes.data.access;
        err.config.headers.Authorization = `Bearer ${phrTokens!.access}`;
        return client.request(err.config);
      }
      return Promise.reject(err);
    },
  );

  return client;
}
```

```tsx
// ht-phr/frontend — mounting the module
const phrClient = await getPhrApiClient();
<LabsUploader apiClient={phrClient} />
```

## Exposed Components

```typescript
// Remote name: "labs_remote"
// Exposes:
'./LabUploads'   // Upload management: list, create, poll progress, review/commit, retry, delete
'./LabResults'   // Lab results: list (grouped by category), detail/trend view, edit, delete
'./types'        // Shared TypeScript interfaces
```

### `<LabUploads />` — Upload Management

Full upload lifecycle in one component. Renders a list of all uploads with inline actions.

| View | Description |
|------|-------------|
| **List** | All uploads grouped by status: in-progress (pending/processing), awaiting review (completed + uncommitted), done, failed |
| **Create** | Upload button → file picker dialog → progress polling |
| **Detail** | Expand an upload to see files, parsed results, error message |
| **Review & commit** | For completed uploads: select/deselect rows, edit values, save all or some |
| **Retry** | Re-run extraction on a failed upload |
| **Delete** | Remove upload + all associated committed lab values |

### `<LabResults />` — Lab Results

All committed lab values. Renders a categorised results grid with detail drill-down.

| View | Description |
|------|-------------|
| **List** | All results grouped by category (Metabolic, Hematology, etc.), filterable by test/date range. Each list item is a rich card — see layout below. |
| **Detail** | Single test trend: full chart (recharts) + historical values list |
| **Edit** | Inline edit value, unit, date, reference range on a single result |
| **Delete** | Remove individual lab result |

**List item card layout** (mirrors existing `LabValueCard`):

```
┌─────────────────────────────────────────────────┐
│  Hemoglobin                    [↑ +0.7] [›]     │  ← test name + trend badge + chevron
│  Blood count                                     │  ← LOINC name (if different from name)
│                                                   │
│  14.2 g/dL                     ┌──────────┐      │  ← latest value + unit
│  Normal: 12.0–17.5 g/dL       │ ~sparkline│      │  ← reference range + mini trend chart
│                                └──────────┘      │     (last 6 values, recharts LineChart)
│                                                   │
│  [Normal]  📎 blood-panel.pdf · 3d ago           │  ← status chip + source badge + time
└─────────────────────────────────────────────────┘
```

Card data per item:
- **Test name** + LOINC name subtitle (when different)
- **Latest value** with unit, formatted to 2 decimal places
- **Reference range** — `Normal: min–max unit` or "No range" italic
- **Reference text** — extra lines from report (if multi-line)
- **Trend badge** — colored pill (green=improving / amber=worsening / gray=stable) with arrow + delta. Color is based on distance-to-range change, not arrow direction (up isn't always good — e.g. LDL rising is bad)
- **Sparkline** — recharts `LineChart` of last 6 values, monotone curve, brand-colored, with hover tooltip showing value + date
- **Status chip** — Normal / Below / Above (hidden for "unknown" when no range exists)
- **Source badge** — file name + time ago (extracted results) or "Manual · You" (manual entry)

Existing implementation: `frontend/src/components/labs/LabValueCard.tsx` (375 lines) — includes `TrendBadge`, `StatusChip`, `Sparkline`, `SparkTooltip` sub-components. The federated `<LabResults />` reuses this component directly, replacing the React Router `<Link>` wrapper with the `onNavigateToDetail` callback prop.

## Props Contract

```typescript
interface LabsBaseProps {
  apiClient: AxiosInstance;          // Authenticated axios instance
  apiBasePath?: string;              // Default: "/api/v1"
  queryClient?: QueryClient;         // Optional; module creates its own if omitted
  className?: string;                // Host can style the root container
  theme?: Partial<LabsThemeTokens>;  // Override CSS custom properties
}

// LabUploads
interface LabUploadsProps extends LabsBaseProps {
  onUploadComplete?: (upload: UploadJob) => void;
  onResultsSaved?: (response: UploadCommitResponse) => void;
}

// LabResults
interface LabResultsProps extends LabsBaseProps {
  /** Host controls navigation to trend detail — if omitted, detail renders inline */
  onNavigateToDetail?: (testAbbreviation: string) => void;
  /** Called after a result is deleted */
  onResultDeleted?: (resultId: number) => void;
  filters?: { test?: string; from?: string; to?: string };
}
```

## Implementation Steps

### Phase 0: Backend Auth Bridge

1. **Add `firebase-admin` to `backend/requirements.txt`** and install.

2. **Add `firebase_uid` field to PHR User model** (`backend/apps/accounts/models.py`):
   - `firebase_uid = CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)`
   - Run `makemigrations` + `migrate`

3. **Initialize Firebase Admin SDK** in `backend/config/settings/base.py`:
   - Read credentials from `FIREBASE_CREDENTIALS_JSON` env var (same as ht-phr uses)
   - Call `firebase_admin.initialize_app()` at settings load time

4. **Create `POST /api/v1/auth/partner-token/` endpoint** — see [Backend Changes](#backend-changes-phr) above for full implementation.

5. **Register URL** in `backend/apps/accounts/urls.py`.

### Phase 1: Frontend Infrastructure (new files only, no breaking changes)

6. **Install deps**
   ```bash
   cd frontend && npm install @module-federation/vite @module-federation/runtime
   ```

7. **Create `frontend/src/federation/` directory** with:
   - `types.ts` — public contract types (LabsBaseProps, LabsUploaderProps, etc.)
   - `LabsContext.tsx` — React Context that provides `apiClient` to internal hooks
   - `LabsProvider.tsx` — wrapper: QueryClientProvider + LabsContext + CSS scope div

8. **Update `vite.config.ts`** — add federation plugin:
   ```typescript
   import { federation } from '@module-federation/vite';
   // ...
   federation({
     name: 'labs_remote',
     filename: 'remoteEntry.js',
     exposes: {
       './LabUploads': './src/federation/LabUploads.tsx',
       './LabResults': './src/federation/LabResults.tsx',
       './types': './src/federation/types.ts',
     },
     shared: {
       react: { singleton: true, requiredVersion: '^18.3.0' },
       'react-dom': { singleton: true, requiredVersion: '^18.3.0' },
       '@tanstack/react-query': { singleton: true, requiredVersion: '^5.0.0' },
       axios: { singleton: true, requiredVersion: '^1.6.0' },
     },
   })
   ```

### Phase 2: API Layer Refactor (backwards-compatible)

9. **Refactor `frontend/src/features/labs/api.ts`** — add optional `apiClient` parameter to each hook:
   ```typescript
   // Before:
   export function useLabResults(filters?: LabResultFilters) {
     // uses global `api`
   }
   // After:
   export function useLabResults(filters?: LabResultFilters, apiClient?: AxiosInstance) {
     const client = apiClient ?? api;
     // uses `client`
   }
   ```
   Existing call sites pass nothing → behavior unchanged.

10. **Create `frontend/src/federation/hooks.ts`** — thin wrappers that pull `apiClient` from context:
   ```typescript
   export function useLabResults(filters?: LabResultFilters) {
     const { apiClient } = useLabsContext();
     return originalUseLabResults(filters, apiClient);
   }
   ```

### Phase 3: Exposed Components

11. **`frontend/src/federation/LabUploads.tsx`** — wraps existing `LabUploadDialog`, `LabUploadReview`, `RecordsChangeLog`:
   - **List**: all uploads grouped by status (in-progress / awaiting review / done / failed)
   - **Create**: upload button → file picker dialog → progress polling
   - **Detail**: expand upload to see files, parsed results, error message
   - **Review & commit**: for completed uploads — select/deselect rows, edit values, save all or some
   - **Retry**: re-run extraction on failed uploads
   - **Delete**: remove upload + all associated committed lab values

12. **`frontend/src/federation/LabResults.tsx`** — wraps existing `LabValueCard`, category grouping from `Records.tsx`, lazy-loaded `LabTrendDetail`:
   - **List**: all committed results grouped by category, filterable by test/date range
   - **Detail**: single test trend chart (recharts) + historical values list
   - **Edit**: inline edit value, unit, date, reference range on a single result
   - **Delete**: remove individual lab result

### Phase 4: CSS Isolation

14. **Create `frontend/tailwind.remote.config.ts`**:
   ```typescript
   const config: Config = {
     ...baseConfig,
     prefix: 'hk-',
     important: '.hk-labs-root',
     content: [
       './src/federation/**/*.{ts,tsx}',
       './src/components/labs/**/*.{ts,tsx}',
       './src/components/ui/**/*.{ts,tsx}',
     ],
   };
   ```

15. **Create `frontend/src/federation/labs.css`** — scoped Tailwind entry with CSS variable defaults under `.hk-labs-root`.

16. **Handle Radix portals** — pass `container` prop (the `.hk-labs-root` element ref) to Dialog/Select/Popover so their portals render inside the scoped root.

### Phase 5: Router Decoupling

17. **Modify `LabValueCard`** — accept optional `onNavigate` prop. When provided, render `<button onClick>` instead of React Router `<Link>`. Existing app passes nothing (keeps `<Link>`).

18. **Modify `RecordsChangeLog`** — accept optional `onDeleteUpload` callback prop for the federated context.

### Phase 6: Dev Harness + Build

19. **Create `frontend/src/federation/dev-harness.tsx`** — standalone dev app that renders all three components with a mock axios instance (for isolated development without the full host app).

20. **Create `frontend/vite.remote.config.ts`** — separate Vite config for building just the remote bundle.

21. **Add scripts to `package.json`**:
    ```json
    "dev:remote": "vite --config vite.remote.config.ts",
    "build:remote": "vite build --config vite.remote.config.ts"
    ```

### Phase 7: Host Consumption Example

22. **Create `frontend/src/federation/README.md`** documenting how external hosts consume:
    ```typescript
    import { init, loadRemote } from '@module-federation/runtime';
    init({
      name: 'partner_host',
      remotes: [{ name: 'labs_remote', entry: 'https://host/remoteEntry.js' }],
    });
    const LabUploads = React.lazy(() => loadRemote('labs_remote/LabUploads'));
    const LabResults = React.lazy(() => loadRemote('labs_remote/LabResults'));

    // Usage:
    <LabUploads apiClient={phrClient} onResultsSaved={() => refetch()} />
    <LabResults apiClient={phrClient} onNavigateToDetail={(abbrev) => router.push(`/labs/${abbrev}`)} />
    ```

## Critical Files

| File | Action |
|------|--------|
| **Backend (auth bridge)** | |
| `backend/requirements.txt` | Modify — add `firebase-admin` |
| `backend/apps/accounts/models.py` | Modify — add `firebase_uid` field |
| `backend/apps/accounts/views.py` | Modify — add `PartnerTokenView` |
| `backend/apps/accounts/urls.py` | Modify — register `/auth/partner-token/` |
| `backend/config/settings/base.py` | Modify — Firebase Admin SDK init |
| **Frontend (federation)** | |
| `frontend/vite.config.ts` | Modify — add federation plugin |
| `frontend/package.json` | Modify — add deps + scripts |
| `frontend/src/features/labs/api.ts` | Modify — add optional apiClient param |
| `frontend/src/components/labs/LabValueCard.tsx` | Modify — add optional onNavigate prop |
| `frontend/src/components/labs/RecordsChangeLog.tsx` | Modify — add optional callbacks |
| `frontend/src/federation/` (new dir) | Create — all federation code |
| `frontend/tailwind.remote.config.ts` | Create — prefixed Tailwind config |
| `frontend/vite.remote.config.ts` | Create — remote build config |
| **Host app (ht-phr)** | |
| `../ht-phr/frontend/src/lib/phr-client.ts` | Create — token exchange + axios factory |

## Known Challenges

1. **Radix portals** render into `document.body` — scoped CSS won't reach them. Fix: pass `container` prop pointing to `.hk-labs-root` div.
2. **Manrope font** — remote's CSS must include its own `@import` for the Google Font since the host may not load it.
3. **recharts (~280KB)** bundled into the remote — intentional; making it shared creates version-lock issues for hosts using different chart libs.
4. **HMR**: Module Federation + Vite HMR can be fragile. The dev harness bypasses MF for day-to-day work.

## Testing Strategy

Three test environments, from fastest iteration to most realistic:

### Level 1: Existing App (no federation)

The quickest way to develop and visually test the components — they already work inside the current app.

```bash
# Terminal 1: Django backend
cd backend && python manage.py runserver 9000

# Terminal 2: Celery worker (for upload processing)
cd backend && LOG_LEVEL=DEBUG celery -A config worker --loglevel=DEBUG

# Terminal 3: Frontend dev server
cd frontend && npm run dev
```

Open `http://localhost:5173/dashboard/records`:
- Upload dialog, progress polling, review/commit → all testable via the Upload button
- Result cards with sparklines, trend badges, status chips → visible in the results grid
- Click a card → trend detail with full chart + history
- Delete uploads/results → via existing UI controls

**What this tests**: Component correctness, API integration, visual fidelity.
**What this does NOT test**: Federation loading, CSS isolation, auth bridge, context injection.

### Level 2: Standalone Dev Harness (federation components, no host)

Renders `<LabUploads />` and `<LabResults />` in isolation, outside the main app. No Module Federation runtime involved — direct imports with the `LabsProvider` context bridge.

```bash
# Terminal 1: Django backend + Celery (same as Level 1)

# Terminal 2: Dev harness
cd frontend && npm run dev:remote    # serves on :5174
```

Open `http://localhost:5174` — a minimal page with:

```
┌──────────────────────────────────────────────┐
│  LabUploads                                   │
│  ┌──────────────────────────────────────────┐ │
│  │ [Upload Report]                          │ │
│  │                                          │ │
│  │ Pending uploads...                       │ │
│  │ Completed uploads awaiting review...     │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  LabResults                                   │
│  ┌──────────────────────────────────────────┐ │
│  │ Metabolic                                │ │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐     │ │
│  │ │Glucose  │ │HbA1c    │ │Creat.   │     │ │
│  │ │14.2 g/dL│ │5.4 %    │ │0.9 mg/dL│     │ │
│  │ │~sparkline│ │~spark.  │ │~spark.  │     │ │
│  │ └─────────┘ └─────────┘ └─────────┘     │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Event log: [callback fired: onResultsSaved]  │
└──────────────────────────────────────────────┘
```

The harness (`frontend/src/federation/dev-harness.tsx`):
- Creates an axios instance with a dev PHR JWT (obtained via `python manage.py shell` or the partner-token endpoint)
- Renders both `<LabUploads />` and `<LabResults />` with the context bridge
- Logs all callback props to an on-screen event log panel (e.g. `onUploadComplete`, `onResultsSaved`, `onNavigateToDetail`, `onResultDeleted`)
- Includes a theme toggle to test CSS variable overrides

**Test checklist for Level 2:**

| Feature | Test |
|---------|------|
| Upload create | Click Upload → pick file → see progress → review parsed rows |
| Upload commit | Select/deselect rows → edit a value → Save → `onResultsSaved` fires |
| Upload retry | Fail an upload (upload a .txt file) → click Retry |
| Upload delete | Delete an upload → confirm it's removed from list + associated results gone |
| Upload polling | Upload a file → watch status transition: pending → processing → completed |
| Results list | See cards grouped by category with sparklines, trend badges, status chips |
| Results detail | Click a card → `onNavigateToDetail` fires with test abbreviation |
| Results edit | Edit a result's value/unit/date → confirm API call succeeds |
| Results delete | Delete a result → confirm it disappears from the list |
| Empty states | No uploads, no results → appropriate empty messages shown |
| Error states | Kill the backend → see error handling in upload and results |
| Theme override | Toggle theme → verify CSS custom properties apply |
| Callback logging | Every callback fires and appears in the event log |

### Level 3: Full Integration (Module Federation + Host App)

Tests the actual federation runtime: remote loading, shared dependency deduplication, CSS isolation, and the auth token exchange.

```bash
# Terminal 1: Django backend + Celery (same as Level 1)

# Terminal 2: PHR frontend (serves remoteEntry.js)
cd frontend && npm run dev           # :5173

# Terminal 3: Test host app
cd frontend/test-host && npm run dev # :5174
```

**Test host app** (`frontend/test-host/`) — a minimal Vite + React app (~50 lines):

```typescript
// test-host/src/App.tsx
import { init, loadRemote } from '@module-federation/runtime';
import React, { Suspense, useEffect, useState } from 'react';
import axios from 'axios';

init({
  name: 'test_host',
  remotes: [{ name: 'labs_remote', entry: 'http://localhost:5173/remoteEntry.js' }],
});

const LabUploads = React.lazy(() => loadRemote('labs_remote/LabUploads'));
const LabResults = React.lazy(() => loadRemote('labs_remote/LabResults'));

function App() {
  const [client, setClient] = useState(null);

  useEffect(() => {
    // Exchange a dev Firebase token for a PHR JWT, or use a hardcoded dev token
    const c = axios.create({
      baseURL: 'http://localhost:9000/api/v1',
      headers: { Authorization: 'Bearer <dev-phr-jwt>' },
    });
    setClient(c);
  }, []);

  if (!client) return <div>Authenticating...</div>;

  return (
    <div style={{ fontFamily: 'sans-serif', padding: 24 }}>
      <h1>Test Host — Labs Module Federation</h1>
      <Suspense fallback={<div>Loading LabUploads...</div>}>
        <LabUploads apiClient={client} />
      </Suspense>
      <hr />
      <Suspense fallback={<div>Loading LabResults...</div>}>
        <LabResults
          apiClient={client}
          onNavigateToDetail={(abbrev) => alert(`Navigate to: ${abbrev}`)}
        />
      </Suspense>
    </div>
  );
}
```

The host intentionally uses **no Tailwind, no shadcn, different fonts** — to surface CSS isolation issues.

**Test checklist for Level 3:**

| Area | Test |
|------|------|
| **Remote loading** | Both `<LabUploads>` and `<LabResults>` render without errors |
| **Shared deps** | Only one React instance in the page (check `React.version` in devtools) |
| **CSS isolation** | Module styled correctly despite host having no Tailwind. Host's `font-family: sans-serif` doesn't bleed into module. |
| **Radix portals** | Upload dialog opens inside the `.hk-labs-root` scope, not `document.body` |
| **Auth bridge** | Token exchange → module API calls succeed with PHR JWT |
| **401 refresh** | Wait 15+ min (or shorten JWT lifetime) → auto-refresh triggers, requests resume |
| **Callback props** | `onNavigateToDetail` / `onResultsSaved` fire correctly in host context |
| **Error boundary** | Kill PHR backend → module shows error state, host app stays alive |
| **Bundle size** | `npm run build:remote` → check `remoteEntry.js` + chunks total. Target: < 500KB gzipped (recharts is ~280KB uncompressed) |
| **HMR** | Edit a component in `src/components/labs/` → change appears in host without full reload (best-effort — known fragile) |

### Playwright E2E Tests

Automated tests for the critical paths that are painful to re-test manually: multi-step async flows, federation loading, and auth. Not for visual polish — that's better tested by eyeballing in the dev harness.

**Setup:**
```bash
cd frontend && npm install -D @playwright/test
npx playwright install chromium
```

**Config** (`frontend/playwright.config.ts`):
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:5174',  // dev harness (Level 2) or test host (Level 3)
  },
  webServer: [
    {
      command: 'python manage.py runserver 9000',
      cwd: '../backend',
      port: 9000,
      reuseExistingServer: true,
    },
    {
      command: 'LOG_LEVEL=INFO celery -A config worker --concurrency=2',
      cwd: '../backend',
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev:remote',
      port: 5174,
      reuseExistingServer: true,
    },
  ],
});
```

**Script** in `package.json`:
```json
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

**Test suite** (`frontend/e2e/`):

#### 1. `upload-flow.spec.ts` — Upload lifecycle (Level 2)

```typescript
test('upload a PDF, poll progress, review results, commit', async ({ page }) => {
  await page.goto('/');

  // Create upload
  await page.getByRole('button', { name: /upload/i }).click();
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('e2e/fixtures/sample-lab-report.pdf');
  await page.getByRole('button', { name: /upload/i }).click();

  // Wait for processing → completed (polling)
  await expect(page.getByText(/reviewing/i)).toBeVisible({ timeout: 30_000 });

  // Review: verify parsed rows appear
  await expect(page.getByText(/Hemoglobin|Glucose|Creatinine/i)).toBeVisible();

  // Commit all results
  await page.getByRole('button', { name: /save/i }).click();

  // Verify callback fired in event log
  await expect(page.getByTestId('event-log')).toContainText('onResultsSaved');
});

test('upload invalid file shows error, retry works', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /upload/i }).click();
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles('e2e/fixtures/not-a-lab-report.txt');
  await page.getByRole('button', { name: /upload/i }).click();

  // Should fail
  await expect(page.getByText(/failed|error|couldn't/i)).toBeVisible({ timeout: 30_000 });
});
```

#### 2. `upload-crud.spec.ts` — Upload CRUD operations (Level 2)

```typescript
test('delete upload removes it from list', async ({ page }) => {
  await page.goto('/');
  // Assumes at least one upload exists from previous test or seed data
  const uploadCard = page.getByTestId('upload-item').first();
  await uploadCard.getByRole('button', { name: /delete/i }).click();

  // Confirm deletion dialog
  await page.getByRole('button', { name: /confirm|yes/i }).click();

  // Upload should disappear
  await expect(uploadCard).not.toBeVisible();
});
```

#### 3. `results-list.spec.ts` — Results display (Level 2)

```typescript
test('results render with value, unit, sparkline, status chip', async ({ page }) => {
  await page.goto('/');

  // At least one result card should be visible
  const card = page.getByTestId('result-card').first();
  await expect(card).toBeVisible();

  // Card has the expected anatomy
  await expect(card.locator('[data-testid="result-value"]')).toBeVisible();
  await expect(card.locator('[data-testid="result-unit"]')).toBeVisible();
  // Sparkline renders as SVG (recharts)
  await expect(card.locator('svg')).toBeVisible();
});

test('clicking result card fires onNavigateToDetail', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('result-card').first().click();
  await expect(page.getByTestId('event-log')).toContainText('onNavigateToDetail');
});
```

#### 4. `results-crud.spec.ts` — Results edit & delete (Level 2)

```typescript
test('delete a lab result removes it from list', async ({ page }) => {
  await page.goto('/');
  const card = page.getByTestId('result-card').first();
  const testName = await card.locator('[data-testid="test-name"]').textContent();

  await card.getByRole('button', { name: /delete/i }).click();
  await page.getByRole('button', { name: /confirm/i }).click();

  // Verify callback fired
  await expect(page.getByTestId('event-log')).toContainText('onResultDeleted');
});
```

#### 5. `federation-smoke.spec.ts` — Federation loading (Level 3)

Runs against the test host app (`:5174`) instead of the dev harness. Requires both the remote (`:5173`) and host to be running.

```typescript
// playwright.config.ts can switch baseURL via env, or use a separate config
test('remote modules load and render in host app', async ({ page }) => {
  await page.goto('http://localhost:5174');

  // Both lazy-loaded components should eventually render
  await expect(page.getByText('LabUploads')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('LabResults')).toBeVisible({ timeout: 15_000 });

  // No console errors about duplicate React instances
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  await page.waitForTimeout(2000);
  expect(errors.filter(e => /react|hook/i.test(e))).toHaveLength(0);
});

test('CSS isolation — host styles do not bleed into module', async ({ page }) => {
  await page.goto('http://localhost:5174');
  await expect(page.locator('.hk-labs-root')).toBeVisible({ timeout: 15_000 });

  // Module root should use Manrope, not host's sans-serif
  const fontFamily = await page.locator('.hk-labs-root').evaluate(
    (el) => getComputedStyle(el).fontFamily
  );
  expect(fontFamily).toContain('Manrope');
});
```

#### 6. `auth-bridge.spec.ts` — Token exchange (Level 3)

```typescript
test('partner-token endpoint returns valid PHR JWT', async ({ request }) => {
  // In CI, use a Firebase test token from a service account
  const res = await request.post('http://localhost:9000/api/v1/auth/partner-token/', {
    data: { firebase_token: process.env.TEST_FIREBASE_TOKEN },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.access).toBeTruthy();
  expect(body.user_id).toBeGreaterThan(0);

  // Use the returned token to call labs API
  const labsRes = await request.get('http://localhost:9000/api/v1/labs/uploads/', {
    headers: { Authorization: `Bearer ${body.access}` },
  });
  expect(labsRes.status()).toBe(200);
});

test('invalid firebase token returns 401', async ({ request }) => {
  const res = await request.post('http://localhost:9000/api/v1/auth/partner-token/', {
    data: { firebase_token: 'invalid-garbage' },
  });
  expect(res.status()).toBe(401);
});
```

**Summary — what Playwright covers vs. what it doesn't:**

| Playwright covers | Test manually / unit test instead |
|---|---|
| Upload flow (create → poll → review → commit) | Sparkline visual appearance |
| Upload error handling + retry | Trend badge color logic (unit test) |
| Upload / result deletion | CSS variable theme overrides |
| Results list rendering + anatomy | Responsive layout breakpoints |
| Federation remote loading smoke test | HMR behavior |
| CSS isolation (font check) | Bundle size (CI build script) |
| Auth token exchange | 401 auto-refresh timing |
| Callback prop firing | Dark mode |

**Test fixtures** (`frontend/e2e/fixtures/`):
- `sample-lab-report.pdf` — a real 1-page lab report that the LLM can parse
- `not-a-lab-report.txt` — a text file to trigger extraction failure

### Backend Auth Tests

```bash
# 1. Valid token → returns PHR JWT + user_id
curl -X POST http://localhost:9000/api/v1/auth/partner-token/ \
  -H 'Content-Type: application/json' \
  -d '{"firebase_token": "<valid-firebase-id-token>"}'
# Expected: 200 { "access": "...", "refresh": "...", "user_id": 1, "created": true }

# 2. Same token again → same user_id, created=false
# Expected: 200 { "access": "...", "refresh": "...", "user_id": 1, "created": false }

# 3. Invalid token → 401
curl -X POST http://localhost:9000/api/v1/auth/partner-token/ \
  -H 'Content-Type: application/json' \
  -d '{"firebase_token": "garbage"}'
# Expected: 401 { "detail": "Invalid Firebase token" }

# 4. Missing token → 400
curl -X POST http://localhost:9000/api/v1/auth/partner-token/ \
  -H 'Content-Type: application/json' \
  -d '{}'
# Expected: 400 { "detail": "firebase_token required" }

# 5. Use returned access token for labs API
curl http://localhost:9000/api/v1/labs/uploads/ \
  -H 'Authorization: Bearer <access-token-from-step-1>'
# Expected: 200 with uploads list
```

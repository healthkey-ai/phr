# Labs Federation Module

Exposes `<LabUploads />` and `<LabResults />` as Module Federation remote components.

## Remote Entry

Build: `npm run build:remote` → `dist/remote/remoteEntry.js`
Dev: `npm run dev:remote` → serves on `:5174` with dev harness

## Host App Integration

```typescript
import { init, loadRemote } from '@module-federation/runtime';
import React, { Suspense } from 'react';

// 1. Initialize Module Federation
init({
  name: 'partner_host',
  remotes: [
    {
      name: 'labs_remote',
      entry: 'https://phr.healthkey.ai/remoteEntry.js', // or localhost:5173 for dev
    },
  ],
});

// 2. Lazy-load components
const LabUploads = React.lazy(() => loadRemote('labs_remote/LabUploads'));
const LabResults = React.lazy(() => loadRemote('labs_remote/LabResults'));

// 3. Create authenticated axios instance (see token exchange below)
const phrClient = await getPhrApiClient();

// 4. Share a single QueryClient so cache invalidation propagates
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

// 5. Render
function LabsPage() {
  return (
    <>
      <Suspense fallback={<div>Loading uploads...</div>}>
        <LabUploads
          apiClient={phrClient}
          queryClient={queryClient}
          onResultsSaved={() => refetchMyData()}
        />
      </Suspense>

      <Suspense fallback={<div>Loading results...</div>}>
        <LabResults
          apiClient={phrClient}
          queryClient={queryClient}
          onNavigateToDetail={(abbrev) => router.push(`/labs/${abbrev}`)}
        />
      </Suspense>
    </>
  );
}
```

## Authentication: Firebase Token Exchange

The PHR backend exposes `POST /api/v1/auth/partner-token/` which accepts a
Firebase ID token and returns a PHR JWT pair. The host app should exchange
its Firebase token before mounting the labs components:

```typescript
import { auth } from '@/lib/firebase';
import axios from 'axios';

const PHR_API_BASE = import.meta.env.VITE_PHR_API_URL;

let phrTokens: { access: string; refresh: string } | null = null;

export async function getPhrApiClient() {
  const firebaseUser = auth.currentUser;
  if (!firebaseUser) throw new Error('Not authenticated');

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

## Props

### `<LabUploads />`

| Prop | Type | Description |
|------|------|-------------|
| `apiClient` | `AxiosInstance` | **Required.** Authenticated axios instance |
| `apiBasePath` | `string` | Default: `/api/v1` |
| `queryClient` | `QueryClient` | Optional; module creates its own if omitted |
| `className` | `string` | Additional class for the root container |
| `theme` | `Partial<LabsThemeTokens>` | Override CSS custom properties |
| `onUploadComplete` | `(upload: UploadJob) => void` | Called when extraction finishes |
| `onResultsSaved` | `(response: UploadCommitResponse) => void` | Called after commit |

### `<LabResults />`

| Prop | Type | Description |
|------|------|-------------|
| `apiClient` | `AxiosInstance` | **Required.** Authenticated axios instance |
| `apiBasePath` | `string` | Default: `/api/v1` |
| `queryClient` | `QueryClient` | Optional; module creates its own if omitted |
| `className` | `string` | Additional class for the root container |
| `theme` | `Partial<LabsThemeTokens>` | Override CSS custom properties |
| `onNavigateToDetail` | `(testAbbreviation: string) => void` | Called when user clicks a result card |
| `onResultDeleted` | `(resultId: number) => void` | Called after a result is deleted |
| `filters` | `{ test?: string; from?: string; to?: string }` | Filter results |

## Sharing a QueryClient

When rendering both `<LabUploads />` and `<LabResults />` on the same page, pass the **same** `QueryClient` instance to both so that cache invalidation propagates (e.g., newly saved results appear immediately in the results list after committing an upload):

```typescript
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

<LabUploads apiClient={phrClient} queryClient={queryClient} />
<LabResults apiClient={phrClient} queryClient={queryClient} />
```

If `queryClient` is omitted, each component creates its own internal instance — fine for standalone use, but cross-component invalidation won't work.

## Shared Dependencies

These are declared as singletons — the host must provide compatible versions:

- `react` ^18.3.0
- `react-dom` ^18.3.0
- `@tanstack/react-query` ^5.0.0
- `axios` ^1.6.0

## Dev Harness

```bash
cd frontend
npm run dev:remote    # starts on :5174
```

Open http://localhost:5174 — log in with your PHR dev credentials, then interact with both components. The event log panel at the bottom shows all callback firings.

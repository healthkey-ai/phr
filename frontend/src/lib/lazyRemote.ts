import { lazy, type ComponentType, type LazyExoticComponent } from "react";

/**
 * lazy() for federated remotes. Plain lazy() caches a rejected import
 * forever — one failed remoteEntry.js fetch (cold start, deploy, flaky
 * network) bricks the page for the whole SPA session. This wrapper retries
 * the import with backoff and bounds each attempt with a timeout so a
 * hanging scale-to-zero remote surfaces the error card instead of an
 * indefinite spinner.
 */
export function lazyRemote<P extends object>(
  importer: () => Promise<{ default: ComponentType<P> }>,
  { retries = 2, timeoutMs = 15000, backoffMs = 1000 } = {},
): LazyExoticComponent<ComponentType<P>> {
  return lazy(async () => {
    let lastError: unknown;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await Promise.race([
          importer(),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error("Remote load timed out")), timeoutMs),
          ),
        ]);
      } catch (error) {
        lastError = error;
        if (attempt < retries) {
          await new Promise((resolve) => setTimeout(resolve, backoffMs * (attempt + 1)));
        }
      }
    }
    throw lastError;
  });
}

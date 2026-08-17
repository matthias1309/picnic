/**
 * Resolves the Vite build's `base` path from the environment (REQ-019).
 *
 * Defaults to today's dev/staging value so a host with no VITE_BASE_PATH
 * set behaves exactly as before. Production sets VITE_BASE_PATH=/ to build
 * a root-relative bundle for its own domain instead.
 *
 * Kept as a small pure function (rather than inlined in vite.config.ts) so
 * it's unit-testable without running an actual Vite build — see
 * frontend/tests/UrlConfig.test.ts.
 */
export function resolveBasePath(env: { VITE_BASE_PATH?: string }): string {
  return env.VITE_BASE_PATH ?? "/picnic-frontend/";
}

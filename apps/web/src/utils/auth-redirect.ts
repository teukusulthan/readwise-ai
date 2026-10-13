/** Where sign-in sends people, and where it sends them back. Used by the guard, the 401 handler and the login form. */

export const LOGIN_PATH = '/login'
export const REGISTER_PATH = '/register'
export const DEFAULT_AFTER_LOGIN = '/books'

export function isAuthPage(pathname: string): boolean {
  return pathname === LOGIN_PATH || pathname === REGISTER_PATH
}

/** `/login?next=<path>` — `next` is the page to return to (omitted for the auth pages themselves). */
export function loginPathFor(next: string): string {
  const pathname = next.split(/[?#]/)[0]
  if (!next || isAuthPage(pathname)) return LOGIN_PATH
  return `${LOGIN_PATH}?next=${encodeURIComponent(next)}`
}

// Browsers drop tabs and newlines from URLs and read `\` as `/`, so `/\t/evil.test` or `/\evil.test` would turn
// into the protocol-relative `//evil.test`. Any such character makes `next` unsafe.
// eslint-disable-next-line no-control-regex
const UNSAFE_NEXT_CHARS = /[\\\u0000-\u001f\u007f]/

/**
 * The `next` query value if it is a path inside this app, else the default page. Rejects absolute and
 * protocol-relative URLs (`https://…`, `//host`, `/\host`, `/\t/host`) so the login page cannot be used as an open
 * redirect: the value must resolve to this origin.
 */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || UNSAFE_NEXT_CHARS.test(next)) return DEFAULT_AFTER_LOGIN
  const base = 'http://app.invalid'
  let resolved: URL
  try {
    resolved = new URL(next, base)
  } catch {
    return DEFAULT_AFTER_LOGIN
  }
  if (resolved.origin !== base || isAuthPage(resolved.pathname)) return DEFAULT_AFTER_LOGIN
  return `${resolved.pathname}${resolved.search}${resolved.hash}`
}

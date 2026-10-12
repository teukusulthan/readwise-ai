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

/**
 * The `next` query value if it is a path inside this app, else the default page. Rejects absolute and
 * protocol-relative URLs (`https://…`, `//host`, `/\host`) so the login page cannot be used as an open redirect.
 */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return DEFAULT_AFTER_LOGIN
  if (isAuthPage(next.split(/[?#]/)[0])) return DEFAULT_AFTER_LOGIN
  return next
}

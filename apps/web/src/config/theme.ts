/**
 * The app ships a single light "cream" theme (tokens in styles/variable.css).
 * Pin the root to light and drop any theme preference persisted by older builds.
 */
export const APP_THEME = 'light' as const

export function applyAppTheme(): void {
  const root = document.documentElement
  root.classList.remove('dark')
  root.classList.add(APP_THEME)
  root.style.colorScheme = APP_THEME
  try {
    localStorage.removeItem('theme-storage')
  } catch {
    // Storage can be unavailable (private mode); the class above is what matters.
  }
}

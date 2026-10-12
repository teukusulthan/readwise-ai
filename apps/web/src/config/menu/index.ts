import { APP_MENU } from './app.menu'
import { ADMINISTRATOR_MENU } from './administrator.menu'

/** Flat list of all menus — use for permission checks, global search, etc. */
export const ALL_MENUS = () => [...APP_MENU, ...ADMINISTRATOR_MENU]

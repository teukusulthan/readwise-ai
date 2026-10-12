import type { IMenu } from '@/types/menu'

// Admin panel menus — only visible to users with role 'admin'.
// Rendered in the admin sidebar, not in AppHeader.
// IDs must be unique across ALL_MENUS — checked against skills/reactjs-menu-config/SKILL.md.

export const ADMINISTRATOR_MENU: IMenu[] = []

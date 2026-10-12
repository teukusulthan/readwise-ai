import type { IMenu } from '@/types/menu'

// Primary navigation rendered by AppSidebar.
// IDs must be unique across ALL_MENUS — checked against skills/reactjs-menu-config/SKILL.md.

export const APP_MENU: IMenu[] = [
  {
    id: 'lbcat1',
    idParent: '',
    display: 'Catalog',
    name: 'book-catalog',
    path: '/books',
    show: true,
    search: true,
    enabled: true,
    group: 'data',
    type: 'menu',
    icon: 'books',
    seo: { title: 'Book catalog', description: 'Browse, import and upload books' },
    privileges: null,
  },
  {
    id: 'lbsrc3',
    idParent: '',
    display: 'Search',
    name: 'search-passages',
    path: '/search',
    show: true,
    search: true,
    enabled: true,
    group: 'data',
    type: 'menu',
    icon: 'magnifying-glass',
    seo: { title: 'Search passages', description: 'Find the passages that match a query across indexed books' },
    privileges: null,
  },
  {
    id: 'lbask2',
    idParent: '',
    display: 'Ask',
    name: 'ask-library',
    path: '/ask',
    show: true,
    search: true,
    enabled: true,
    group: 'data',
    type: 'menu',
    icon: 'chat-circle-text',
    seo: { title: 'Ask the library', description: 'Questions answered from indexed books with sources' },
    privileges: null,
  },
]

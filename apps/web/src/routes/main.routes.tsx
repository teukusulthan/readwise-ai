import { lazy, Suspense } from 'react'
import { Navigate, RouteObject } from 'react-router-dom'
import AppLayout from '@/components/layouts/AppLayout'
import type { IRouteHandle } from '@/types/route'

const CatalogPage = lazy(() => import('@/pages/library/CatalogPage'))
const BookDetailPage = lazy(() => import('@/pages/library/BookDetailPage'))
const AskPage = lazy(() => import('@/pages/library/AskPage'))

const mainRoutes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/books" replace /> },
      { path: '/books', element: <Suspense><CatalogPage /></Suspense> },
      // Detail route: reached from catalog cards, not a menu entry.
      { path: '/books/:id', element: <Suspense><BookDetailPage /></Suspense> },
      // Chat: `/ask` = new chat, `/ask/:conversationId` = saved conversation. Fills the main column.
      { path: '/ask/:conversationId?', element: <Suspense><AskPage /></Suspense>, handle: { fullHeight: true } satisfies IRouteHandle },
      { path: '*', element: <Navigate to="/books" replace /> },
    ],
  },
]

export default mainRoutes

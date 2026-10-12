import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import env from '@/config/env'
import { buildAppRoutes } from './app.routes'

const router = createBrowserRouter(buildAppRoutes(env.auth.enabled))

const RouteIndex = () => {
  return <RouterProvider router={router} />
}

export default RouteIndex

import { createBrowserRouter, RouterProvider } from 'react-router-dom'


import mainRoutes from './main.routes'

const router = createBrowserRouter([...mainRoutes])

const RouteIndex = () => {
  return (
      <RouterProvider router={router} />
  )
}

export default RouteIndex

import React from 'react'
import { RouteObject } from 'react-router-dom'

const LoginPage = React.lazy(() => import('@/pages/auth/LoginPage'))

const authRoutes: RouteObject[] = [
  {
    path: 'auth',
    children: [
      {
        path: 'login',
        element: <LoginPage />,
      },
      // You can add register, forgot-password, etc. here
    ],
  },
]

export default authRoutes

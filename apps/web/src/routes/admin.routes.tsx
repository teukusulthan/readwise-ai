import { RouteObject } from 'react-router-dom'
import RoleGuard from './guards/RoleGuard'

const adminRoutes: RouteObject[] = [
  {
    path: 'administrator',
    element: (
      <RoleGuard allowedRoles={['admin']}>
        <></>
      </RoleGuard>
    ),
  },
]

export default adminRoutes

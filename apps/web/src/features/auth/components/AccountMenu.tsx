import { Button } from '@/components/ui/button'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { useAuthStore } from '@/stores/useAuthStore'
import { renderIcon } from '@/utils/icon-renderer'

/** Header block (only with VITE_AUTH_ENABLED): who is signed in, and "Sign out". */
export function AccountMenu() {
  const user = useAuthStore((state) => state.user)
  const logout = useLogout()
  if (!user) return null
  const name = user.fullname?.trim() || user.username

  return (
    <div className="ml-auto flex min-w-0 items-center gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary-bold" aria-hidden>
        {renderIcon({ icon: 'user', className: 'text-[18px]' })}
      </span>
      <span className="hidden min-w-0 flex-col leading-tight sm:flex">
        <span className="truncate text-body-md font-semibold text-font-primary">{name}</span>
        <span className="truncate text-body-sm text-font-secondary">{user.email}</span>
      </span>
      <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
        {renderIcon({ icon: 'sign-out' })}
        Sign out
      </Button>
    </div>
  )
}

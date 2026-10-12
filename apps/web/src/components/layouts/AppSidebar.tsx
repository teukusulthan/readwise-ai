import { NavLink } from 'react-router-dom'

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { APP_MENU } from '@/config/menu/app.menu'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

/** Primary navigation — rendered from APP_MENU only. Collapses to an icon rail on small screens. */
export default function AppSidebar() {
  const items = APP_MENU.filter((item) => item.show && item.enabled && !item.idParent)

  return (
    <aside
      className="app-sidebar flex w-[4.5rem] shrink-0 flex-col border-r border-border-primary bg-background-primary md:w-[15.5rem]"
      aria-label="Main navigation"
    >
      <nav className="flex flex-col gap-1.5 p-3 md:p-4">
        <p className="mb-1 hidden px-3 text-label-sm font-semibold uppercase tracking-widest text-font-placeholder md:block">Library</p>
        {items.map((item) => (
          <Tooltip key={item.id}>
            {/* The trigger wraps the link: Radix's asChild would turn NavLink's className function into a string. */}
            <TooltipTrigger asChild>
              <div>
                <NavLink
                  to={item.path}
                  aria-label={item.display}
                  className={({ isActive }) =>
                    cn(
                      'group/nav relative flex h-11 items-center justify-center gap-3 overflow-hidden rounded-xl px-3 text-body-md font-medium md:justify-start',
                      'transition-[background-color,color,box-shadow,scale] duration-200 ease-fluid active:scale-[0.98] active:duration-75',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      isActive
                        ? 'bg-primary-light text-primary-bold shadow-xs ring-1 ring-primary-soft/60'
                        : 'text-font-secondary hover:bg-background-secondary hover:text-font-primary',
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {/* Active marker: springs in on the current page. */}
                      <span
                        aria-hidden="true"
                        className={cn(
                          'absolute inset-y-2.5 left-0 w-1 origin-center rounded-r-full bg-primary transition-[scale,opacity] duration-300 ease-spring',
                          isActive ? 'scale-y-100 opacity-100' : 'scale-y-0 opacity-0',
                        )}
                      />
                      {renderIcon({
                        icon: item.icon,
                        weight: isActive ? 'fill' : 'regular',
                        className: 'text-[20px] transition-transform duration-200 ease-fluid group-hover/nav:-translate-y-px group-hover/nav:scale-110',
                      })}
                      <span className="hidden md:inline">{item.display}</span>
                    </>
                  )}
                </NavLink>
              </div>
            </TooltipTrigger>
            {/* Labels are visible on wide screens; the tooltip is for the icon rail. */}
            <TooltipContent side="right" className="md:hidden">
              {item.display}
            </TooltipContent>
          </Tooltip>
        ))}
      </nav>
    </aside>
  )
}

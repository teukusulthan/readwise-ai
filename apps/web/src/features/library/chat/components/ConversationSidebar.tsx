import { useMemo, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Hint } from '@/components/ui/tooltip'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { useConversations, useDeleteConversation, useRenameConversation } from '@/features/library/chat/hooks/useConversations'
import type { IConversation } from '@/features/library/chat/types/conversation.types'
import { groupConversations } from '@/features/library/chat/utils/chat-thread'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface ConversationSidebarProps {
  activeId: string | undefined
  onNewChat: () => void
  /** Called after the active conversation is deleted. */
  onActiveDeleted: () => void
  /** Called when a conversation link is followed (e.g. to close the mobile drawer). */
  onNavigate?: () => void
  className?: string
}

/** Saved conversations, grouped by last activity. Rename inline, delete with confirmation. */
export function ConversationSidebar({ activeId, onNewChat, onActiveDeleted, onNavigate, className }: ConversationSidebarProps) {
  const conversations = useConversations()
  const rename = useRenameConversation()
  const remove = useDeleteConversation()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<IConversation | null>(null)
  const groups = useMemo(() => groupConversations(conversations.data ?? []), [conversations.data])

  const confirmDelete = () => {
    if (!pendingDelete) return
    const deletingActive = pendingDelete.id === activeId
    remove.mutate(pendingDelete.id, {
      onSuccess: () => {
        setPendingDelete(null)
        if (deletingActive) onActiveDeleted()
      },
    })
  }

  return (
    <div className={cn('flex min-h-0 flex-col', className)}>
      <div className="p-4">
        <Button className="w-full" onClick={onNewChat}>
          {renderIcon({ icon: 'plus', weight: 'bold' })}
          New chat
        </Button>
      </div>

      <div className="relative min-h-0 flex-1">
        <PerfectScrollArea className="h-full" options={{ wheelPropagation: false }}>
          <nav aria-label="Conversations" className="flex flex-col gap-5 px-3 pb-6">
            {conversations.isLoading && (
              <div className="flex flex-col gap-2 px-1" aria-busy="true">
                <Skeleton className="h-9" />
                <Skeleton className="h-9" />
                <Skeleton className="h-9 w-2/3" />
              </div>
            )}
            {conversations.error && (
              <p role="alert" className="px-3 text-body-sm text-error-bold">
                Could not load conversations: {conversations.error.message}
              </p>
            )}
            {conversations.data?.length === 0 && (
              <p className="px-3 text-body-sm text-font-placeholder">No conversations yet. Your chats are saved here automatically.</p>
            )}

            {groups.map((group) => (
              <section key={group.label} className="flex flex-col gap-1">
                <h3 className="px-3 pb-1 text-label-sm font-semibold uppercase tracking-widest text-font-placeholder">{group.label}</h3>
                {group.items.map((conversation) =>
                  editingId === conversation.id ? (
                    <RenameField
                      key={conversation.id}
                      initial={conversation.title}
                      onDone={(title) => {
                        setEditingId(null)
                        if (title && title !== conversation.title) rename.mutate({ id: conversation.id, title })
                      }}
                    />
                  ) : (
                    <div key={conversation.id} className="group relative">
                      <Hint label={conversation.title} side="right">
                        <NavLink
                          to={`/ask/${conversation.id}`}
                          onClick={onNavigate}
                          className={cn(
                            'flex h-10 items-center rounded-lg pr-16 pl-3 text-body-md transition-[background-color,color,padding,scale] duration-200 ease-fluid active:scale-[0.98] active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                            conversation.id === activeId
                              ? 'bg-primary-light font-medium text-primary-bold'
                              : 'text-font-secondary hover:bg-background-secondary hover:pl-4 hover:text-font-primary',
                          )}
                        >
                          <span className="truncate">{conversation.title}</span>
                        </NavLink>
                      </Hint>
                      <div
                        className={cn(
                          'absolute top-1/2 right-1.5 flex -translate-y-1/2 gap-0.5 transition-[opacity,translate] duration-200 ease-fluid',
                          conversation.id === activeId
                            ? 'opacity-100'
                            : 'translate-x-1 opacity-0 group-focus-within:translate-x-0 group-focus-within:opacity-100 group-hover:translate-x-0 group-hover:opacity-100',
                        )}
                      >
                        <IconAction icon="pencil-simple" label="Rename" ariaLabel={`Rename “${conversation.title}”`} onClick={() => setEditingId(conversation.id)} />
                        <IconAction icon="trash" label="Delete" ariaLabel={`Delete “${conversation.title}”`} danger onClick={() => setPendingDelete(conversation)} />
                      </div>
                    </div>
                  ),
                )}
              </section>
            ))}
          </nav>
        </PerfectScrollArea>
      </div>

      <Dialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this conversation?</DialogTitle>
            <DialogDescription>
              “{pendingDelete?.title}” and all its messages will be removed permanently. Your books are not affected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={remove.isPending} onClick={confirmDelete}>
              {renderIcon({ icon: 'trash' })}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

interface IconActionProps {
  icon: string
  /** Short tooltip text. */
  label: string
  /** Full name for screen readers (which conversation). */
  ariaLabel: string
  onClick: () => void
  danger?: boolean
}

function IconAction({ icon, label, ariaLabel, onClick, danger = false }: IconActionProps) {
  return (
    <Hint label={label}>
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={onClick}
        className={cn(
          'flex size-7 items-center justify-center rounded-md text-font-secondary transition-[background-color,color,scale] duration-200 ease-fluid hover:scale-110 active:scale-90 active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          danger ? 'hover:bg-error-light hover:text-error-bold' : 'hover:bg-background-primary hover:text-font-primary',
        )}
      >
        {renderIcon({ icon, className: 'text-[15px]' })}
      </button>
    </Hint>
  )
}

/** Inline title editor: Enter or leaving the field saves, Escape cancels. */
function RenameField({ initial, onDone }: { initial: string; onDone: (title: string | null) => void }) {
  const [value, setValue] = useState(initial)
  const finished = useRef(false)
  // Enter/Escape unmount the field, which can also fire blur — finish only once.
  const finish = (title: string | null) => {
    if (finished.current) return
    finished.current = true
    onDone(title)
  }
  return (
    <input
      autoFocus
      aria-label="Conversation title"
      value={value}
      maxLength={120}
      onChange={(event) => setValue(event.target.value)}
      onFocus={(event) => event.target.select()}
      onBlur={() => finish(value.trim() || null)}
      onKeyDown={(event) => {
        if (event.key === 'Enter') finish(value.trim() || null)
        if (event.key === 'Escape') finish(null)
      }}
      className="h-10 w-full rounded-lg border border-primary-soft bg-background-primary px-3 text-body-md text-font-primary shadow-xs focus:outline-none focus:ring-2 focus:ring-ring"
    />
  )
}

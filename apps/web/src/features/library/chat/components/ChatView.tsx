import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { smoothScrollTo } from '@/components/wrappers/inertia-scroll'
import { useActiveTurn } from '@/features/library/chat/hooks/useActiveTurn'
import { useAskStream } from '@/features/library/chat/hooks/useAskStream'
import { useConversation } from '@/features/library/chat/hooks/useConversations'
import { useIndexedBooks } from '@/features/library/hooks/useIndexedBooks'
import { useSmoothText } from '@/features/library/chat/hooks/useSmoothText'
import type { TChatMessage } from '@/features/library/chat/types/conversation.types'
import { pendingVisibility } from '@/features/library/chat/utils/chat-thread'
import { CONVERSATION_KEYS } from '@/features/library/constants/query-keys'
import type { IBook } from '@/features/library/types/book.types'
import { renderIcon } from '@/utils/icon-renderer'
import { AssistantMessage, type IAssistantView } from './AssistantMessage'
import { ChatComposer } from './ChatComposer'
import { ChatEmptyState } from './ChatEmptyState'
import { ConversationSidebar } from './ConversationSidebar'
import { UserMessage } from './UserMessage'

const NO_MESSAGES: TChatMessage[] = []
// Within this distance of the bottom, new text keeps the thread scrolled to the end.
const STICK_THRESHOLD_PX = 80

/** Chat page: saved conversations | message thread with the composer pinned underneath. */
export function ChatView() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const indexedBooks = useIndexedBooks()
  const conversation = useConversation(conversationId)
  const activeTurn = useActiveTurn(conversationId)
  const { state, ask, attach, cancel, detach, reset, isStreaming, isStopping } = useAskStream()

  const [selectedIds, setSelectedIds] = useState<string[]>(() => searchParams.getAll('bookId'))
  const [pendingFrom, setPendingFrom] = useState(0)
  const [draft, setDraft] = useState<{ text: string; key: number }>()
  const [historyOpen, setHistoryOpen] = useState(false)
  /** Fetching the saved copy of the previous turn before a new question is sent. */
  const [preparingSend, setPreparingSend] = useState(false)
  /** Changes only when the user opens another conversation (not when a new chat gets its URL): the thread fades in. */
  const [threadKey, setThreadKey] = useState(conversationId ?? 'new')
  /** A finished turn whose saved copy should be fetched once its text is fully revealed. */
  const [settled, setSettled] = useState<{ conversationId: string | null } | null>(null)

  /** Conversation created/continued by the live turn: navigating to it must not reset the turn. */
  const ownConversationId = useRef<string | null>(null)
  const restoredScopeFor = useRef<string | null>(null)
  const attachCheckedFor = useRef<string | null>(null)
  const routeConversationId = useRef(conversationId)
  routeConversationId.current = conversationId
  const previousConversationId = useRef(conversationId)
  const scrollRef = useRef<HTMLElement | null>(null)
  const stickToBottom = useRef(true)

  const saved = conversation.data?.messages ?? NO_MESSAGES
  // Covers and authors for the "based on these books" cards (indexed books are already loaded for the picker).
  const booksById = useMemo(() => new Map<string, IBook>((indexedBooks.books ?? []).map((book) => [book.id, book])), [indexedBooks.books])

  // Opening another conversation (or "New chat") leaves the previous live turn. It is only
  // disconnected: the server finishes and saves that answer, and re-opening re-attaches to it.
  useEffect(() => {
    stickToBottom.current = true
    const previous = previousConversationId.current
    previousConversationId.current = conversationId
    if (conversationId && conversationId === ownConversationId.current) return
    // Its cached thread misses whatever happens server-side meanwhile (the running answer, or
    // everything after a new chat's empty seed): fetch it again when the user comes back.
    if (previous && previous !== conversationId) void queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.detail(previous) })
    ownConversationId.current = null
    restoredScopeFor.current = null
    attachCheckedFor.current = null
    setThreadKey(conversationId ?? 'new')
    detach()
    reset()
  }, [conversationId, detach, reset, queryClient])

  // Reopening a conversation restores the books it was asking.
  useEffect(() => {
    const data = conversation.data
    if (!data || restoredScopeFor.current === data.id) return
    restoredScopeFor.current = data.id
    if (data.id !== ownConversationId.current) setSelectedIds(data.bookIds)
  }, [conversation.data])

  // Opening (or reloading, or coming back to) a conversation whose answer is still being
  // generated: re-attach to it. Waits for this visit's fresh thread and active-turn answer.
  const activeTurnData = activeTurn.data
  const checkingActive = conversation.isFetching || activeTurn.isFetching
  useEffect(() => {
    const data = conversation.data
    if (!data || !activeTurnData || checkingActive) return
    if (attachCheckedFor.current === data.id || data.id === ownConversationId.current) return
    attachCheckedFor.current = data.id
    if (!activeTurnData.active) return
    const index = data.messages.map((message) => message.role).lastIndexOf('user')
    ownConversationId.current = data.id
    stickToBottom.current = true
    setPendingFrom(Math.max(index, 0))
    void attach(activeTurnData.sessionId, index >= 0 ? data.messages[index].content : '', data.id, {
      onSettled: (id) => setSettled({ conversationId: id }),
    })
  }, [conversation.data, activeTurnData, checkingActive, attach])

  const refreshHistory = useCallback(
    (id: string | null) => {
      if (id) void queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.detail(id) })
      void queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.list })
    },
    [queryClient],
  )

  const send = async (question: string) => {
    stickToBottom.current = true
    let from = saved.length
    // The previous turn is still drawn only locally (e.g. just stopped): load its saved copy
    // first, so it stays on screen and the new question is placed after it.
    if (conversationId && live && (showQuestion || showAnswer)) {
      setPreparingSend(true)
      const refreshed = await conversation.refetch()
      setPreparingSend(false)
      if (routeConversationId.current !== conversationId) return
      from = refreshed.data?.messages.length ?? from
    }
    setPendingFrom(from)
    void ask(
      { question, bookIds: selectedIds.length ? selectedIds : undefined, conversationId },
      {
        onConversation: (created) => {
          ownConversationId.current = created.id
          if (!conversationId) {
            // Seed the new conversation so the URL can switch without a fetch or a flash.
            queryClient.setQueryData(CONVERSATION_KEYS.detail(created.id), { ...created, messages: [] })
            navigate(`/ask/${created.id}`, { replace: true })
          }
          void queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.list })
        },
        onSettled: (id) => setSettled({ conversationId: id }),
      },
    )
  }

  // The server stops generating, saves the partial answer and ends the stream with `cancelled`;
  // onSettled then refreshes the history. Send stays blocked until then (isStopping).
  const stop = () => cancel()

  const startNewChat = () => {
    setHistoryOpen(false)
    navigate('/ask')
  }

  // ── live turn ─────────────────────────────────────────────────────
  const live = state.phase !== 'idle'
  const { showQuestion, showAnswer } = live ? pendingVisibility(saved, pendingFrom, state.question) : { showQuestion: false, showAnswer: false }
  // Providers deliver tokens in bursts; reveal them at a steady pace (see useSmoothText).
  const answerText = useSmoothText(state.final?.answer ?? state.text, isStreaming ? 'stream' : state.phase === 'done' ? 'finish' : 'instant')
  // Until the text has caught up, the answer still looks like it is being written.
  const revealing = state.phase === 'done' && answerText.catchingUp
  const final = revealing ? null : state.final
  const liveAnswer: IAssistantView = {
    id: 'live',
    content: answerText.text,
    mode: final?.mode ?? (state.phase === 'stopped' ? 'stopped' : null),
    grounded: final?.grounded ?? true,
    sources: final?.sources ?? state.sources,
    skippedBooks: final?.skippedBooks ?? state.skippedBooks,
    model: final?.model ?? null,
    error: state.error,
  }

  // One short spoken message per turn (failures are spoken by the answer's role="alert" instead). The streaming text itself is not a live region (it would
  // be read token by token); this region only changes when the turn ends.
  const announcement = revealing
    ? ''
    : state.phase === 'done'
      ? 'Answer ready'
      : state.phase === 'stopped'
        ? 'Answer stopped'
        : ''

  // The refetched conversation replaces the live bubble, so wait until its text is fully shown.
  useEffect(() => {
    if (!settled || revealing) return
    refreshHistory(settled.conversationId)
    setSettled(null)
  }, [settled, revealing, refreshHistory])

  // ── scrolling ─────────────────────────────────────────────────────
  // Follow the newest text while the user is at the bottom. Only the user's own scrolling
  // (wheel, touch, scrollbar, keys) can stop that — never our own smooth follow.
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return
    let lastUserInput = 0
    const markUserInput = () => {
      lastUserInput = performance.now()
    }
    const onWheel = (event: WheelEvent) => {
      markUserInput()
      if (event.deltaY < 0) stickToBottom.current = false // reading back: stop following at once
    }
    const onScroll = () => {
      const nearBottom = element.scrollHeight - element.scrollTop - element.clientHeight < STICK_THRESHOLD_PX
      if (nearBottom) stickToBottom.current = true
      else if (performance.now() - lastUserInput < 400) stickToBottom.current = false
    }
    element.addEventListener('wheel', onWheel, { passive: true })
    element.addEventListener('touchmove', markUserInput, { passive: true })
    element.addEventListener('pointerdown', markUserInput, { passive: true })
    element.addEventListener('keydown', markUserInput)
    element.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      element.removeEventListener('wheel', onWheel)
      element.removeEventListener('touchmove', markUserInput)
      element.removeEventListener('pointerdown', markUserInput)
      element.removeEventListener('keydown', markUserInput)
      element.removeEventListener('scroll', onScroll)
    }
  }, [])

  // Opening a conversation jumps straight to its end; new text afterwards glides into view.
  const followedThread = useRef<string | null>(null)
  useLayoutEffect(() => {
    const element = scrollRef.current
    if (!element || !stickToBottom.current) return
    if (followedThread.current !== threadKey) {
      followedThread.current = threadKey
      element.scrollTop = element.scrollHeight
    } else {
      smoothScrollTo(element, element.scrollHeight)
    }
  }, [saved, answerText.text, state.phase, showAnswer, threadKey, state.reconnecting])

  const notFound = !!conversationId && !!conversation.error
  const loadingConversation = !!conversationId && conversation.isLoading
  const empty = !conversationId && !live
  const title = conversationId ? (conversation.data?.title ?? (live ? state.question : '')) : 'New chat'

  return (
    <div className="flex h-full min-h-0">
      <ConversationSidebar
        activeId={conversationId}
        onNewChat={startNewChat}
        onActiveDeleted={() => navigate('/ask', { replace: true })}
        className="hidden w-72 shrink-0 border-r border-border-primary bg-background-primary lg:flex"
      />

      <section className="flex min-w-0 flex-1 flex-col" aria-label="Chat">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border-primary bg-background-primary/70 px-4 md:px-6">
          <Button variant="ghost" size="icon" className="size-9 lg:hidden" aria-label="Show conversations" onClick={() => setHistoryOpen(true)}>
            {renderIcon({ icon: 'list', className: 'text-[18px]' })}
          </Button>
          <h2 className="min-w-0 flex-1 truncate font-serif text-h6 font-semibold text-font-primary" title={title}>
            {title}
          </h2>
          {conversationId && (
            <Button variant="ghost" size="xs" onClick={startNewChat}>
              {renderIcon({ icon: 'note-pencil', className: 'text-[16px]' })}
              <span className="hidden sm:inline">New chat</span>
            </Button>
          )}
        </header>

        <p role="status" aria-live="polite" aria-atomic="true" className="sr-only" data-testid="answer-announcement">
          {announcement}
        </p>

        <div className="relative min-h-0 flex-1">
          <PerfectScrollArea ref={scrollRef} className="h-full" options={{ wheelPropagation: false }}>
            <div key={threadKey} className="mx-auto flex min-h-full w-full max-w-3xl animate-page-in flex-col gap-8 px-5 py-8 md:px-8">
              {notFound && (
                <div role="alert" className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
                  <p className="font-serif text-h4 font-semibold text-font-primary">This conversation doesn’t exist</p>
                  <p className="text-body-md text-font-secondary">It may have been deleted.</p>
                  <Button onClick={startNewChat}>Start a new chat</Button>
                </div>
              )}

              {loadingConversation && (
                <div className="flex flex-col gap-6" aria-busy="true">
                  <Skeleton className="ml-auto h-12 w-2/3 rounded-2xl" />
                  <Skeleton className="h-32 w-full rounded-2xl" />
                  <Skeleton className="ml-auto h-12 w-1/2 rounded-2xl" />
                </div>
              )}

              {empty && (
                <ChatEmptyState bookTitles={(indexedBooks.books ?? []).map((book) => book.title)} onPick={(text) => setDraft({ text, key: Date.now() })} />
              )}

              {saved.map((message) =>
                message.role === 'user' ? (
                  <UserMessage key={message.id} content={message.content} />
                ) : (
                  <AssistantMessage key={message.id} message={message} booksById={booksById} />
                ),
              )}

              {live && showQuestion && <UserMessage content={state.question} animate />}
              {live && showAnswer && <AssistantMessage key={`live-${pendingFrom}`} message={liveAnswer} phase={revealing ? 'generating' : state.phase} booksById={booksById} animate />}
              {state.reconnecting && (
                <p role="status" className="flex items-center gap-2 self-center rounded-full border border-warning-soft/70 bg-warning-light px-4 py-1.5 text-body-sm text-warning-bold">
                  {renderIcon({ icon: 'wifi-slash', className: 'text-[16px]' })}
                  Connection lost — reconnecting. The answer keeps going on the server.
                </p>
              )}
            </div>
          </PerfectScrollArea>
        </div>

        <div className="shrink-0 px-4 pt-2 pb-5 md:px-8">
          <div className="mx-auto w-full max-w-3xl">
            <ChatComposer
              selectedIds={selectedIds}
              onSelectedIdsChange={setSelectedIds}
              isStreaming={isStreaming}
              sendBlocked={isStopping || preparingSend}
              disabled={indexedBooks.books?.length === 0 || notFound}
              onSend={(question) => void send(question)}
              onStop={stop}
              draft={draft}
            />
          </div>
        </div>
      </section>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-md">
          <DialogTitle>Conversations</DialogTitle>
          <DialogDescription className="sr-only">Your saved chats. Pick one to continue it.</DialogDescription>
          <ConversationSidebar
            activeId={conversationId}
            onNewChat={startNewChat}
            onActiveDeleted={() => navigate('/ask', { replace: true })}
            onNavigate={() => setHistoryOpen(false)}
            className="-mx-4 h-[60vh] min-w-0"
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

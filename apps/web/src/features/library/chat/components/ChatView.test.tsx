import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TooltipProvider } from '@/components/ui/tooltip'
import { STOP_GRACE_MS } from '@/features/library/chat/hooks/useAskStream'
import type { IActiveSession, TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import type { IConversation, IConversationDetail, TChatMessage } from '@/features/library/chat/types/conversation.types'
import { bookService } from '@/services/book.service'
import { chatService } from '@/services/chat.service'
import { conversationService } from '@/services/conversation.service'
import { ChatView } from './ChatView'

type TOnEvent = (event: TChatStreamEvent, id: string) => void

/** One open answer stream (POST /chat/stream or a resume) that the test drives by hand. */
interface IOpenStream {
  kind: 'stream' | 'resume'
  args: unknown[]
  signal: AbortSignal | undefined
  emit: TOnEvent
  finish: () => void
}

const NOW = new Date().toISOString()
const conversation = (id: string, title: string): IConversation => ({ id, title, bookIds: [], createdAt: NOW, updatedAt: NOW })
const userMessage = (id: string, content: string): TChatMessage => ({ id, role: 'user', content, bookIds: [], createdAt: NOW })
const assistantMessage = (id: string, content: string, mode: 'llm' | 'stopped' = 'llm'): TChatMessage => ({
  id,
  role: 'assistant',
  content,
  mode,
  grounded: false,
  sources: [],
  skippedBooks: [],
  model: 'm',
  error: null,
  createdAt: NOW,
})

// "Server" state the mocked services read; tests change it as the backend would.
let conversations: IConversation[]
let details: Record<string, IConversationDetail>
let active: Record<string, IActiveSession>
let streams: IOpenStream[]

function openStream(kind: IOpenStream['kind'], args: unknown[], { signal, onEvent }: { signal?: AbortSignal; onEvent: TOnEvent }) {
  return new Promise<void>((resolve) => {
    streams.push({ kind, args, signal, emit: (event, id) => act(() => onEvent(event, id)), finish: resolve })
  })
}

beforeEach(() => {
  conversations = [conversation('a', 'Alpha'), conversation('b', 'Beta')]
  details = {
    a: { ...conversation('a', 'Alpha'), messages: [] },
    b: { ...conversation('b', 'Beta'), messages: [userMessage('b1', 'Other question'), assistantMessage('b2', 'Other answer')] },
  }
  active = {}
  streams = []
  vi.spyOn(bookService, 'getAll').mockResolvedValue({ data: [{ id: 'book-1', title: 'Dune' }] } as never)
  vi.spyOn(conversationService, 'getAll').mockImplementation(async () => ({ data: [...conversations] }) as never)
  vi.spyOn(conversationService, 'getOne').mockImplementation(async (id) => {
    if (!details[id]) throw new Error('Not found')
    return { data: structuredClone(details[id]) } as never
  })
  vi.spyOn(chatService, 'active').mockImplementation(
    async (id) => ({ data: active[id] ?? { active: false, sessionId: '', conversationId: id } }) as never,
  )
  vi.spyOn(chatService, 'stream').mockImplementation((payload, options) => openStream('stream', [payload], options))
  vi.spyOn(chatService, 'resume').mockImplementation((sessionId, afterId, options) => openStream('resume', [sessionId, afterId], options))
  vi.spyOn(chatService, 'cancel').mockResolvedValue({ data: { cancelled: true } } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function renderChat(path: string) {
  // Same caching as the app (src/config/query-client.ts): threads stay fresh for 5 minutes.
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 5 * 60_000, retry: false, refetchOnWindowFocus: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/ask/:conversationId?" element={<ChatView />} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

// Label / href lookups: role queries are slow on this large tree.
const sendButton = () => screen.getByLabelText('Send')

const askStreams = () => streams.filter((s) => s.kind === 'stream')

/** Types and sends a question; resolves with the POST /chat/stream it opened. */
async function askAndGetStream(question: string): Promise<IOpenStream> {
  const before = askStreams().length
  fireEvent.change(screen.getByLabelText('Your question'), { target: { value: question } })
  await waitFor(() => expect(sendButton()).toBeEnabled())
  fireEvent.click(sendButton())
  await waitFor(() => expect(askStreams()).toHaveLength(before + 1))
  return askStreams()[before]
}

const conversationLink = (id: string) => document.querySelector<HTMLAnchorElement>(`nav a[href="/ask/${id}"]`)
const openConversation = (id: string) => fireEvent.click(conversationLink(id) as HTMLAnchorElement)
/** The sidebar has loaded and lists this conversation. */
const sidebarLists = (id: string) => waitFor(() => expect(conversationLink(id)).not.toBeNull())

// Full page renders (sidebar, composer, thread) take a second or two each in jsdom.
const PAGE_TEST = { timeout: 15_000 }

describe('ChatView — leaving and coming back to a running answer', PAGE_TEST, () => {
  it('re-attaches to the turn and shows the latest thread', async () => {
    renderChat('/ask/a')
    await sidebarLists('a')

    const first = await askAndGetStream('First question')
    first.emit({ type: 'session', sessionId: 's1' }, '1-0')
    first.emit({ type: 'conversation', conversation: conversation('a', 'Alpha') }, '2-0')
    first.emit({ type: 'delta', text: 'Partial' }, '3-0')
    // Server side: the question is saved and the answer keeps being generated.
    details.a.messages = [userMessage('a1', 'First question')]
    active.a = { active: true, sessionId: 's1', conversationId: 'a' }

    openConversation('b')
    expect(await screen.findByText('Other answer')).toBeInTheDocument()
    expect(first.signal?.aborted).toBe(true) // only disconnected: the server keeps going
    expect(screen.queryByText('First question')).not.toBeInTheDocument()

    openConversation('a')
    await waitFor(() => expect(streams.some((s) => s.kind === 'resume')).toBe(true))
    const resumed = streams.find((s) => s.kind === 'resume') as IOpenStream
    expect(resumed.args).toEqual(['s1', '0']) // replays the running answer from the start
    resumed.emit({ type: 'delta', text: 'Partial answer, continued' }, '3-0')

    expect(await screen.findByText('Partial answer, continued')).toBeInTheDocument()
    expect(screen.getAllByText('First question')).toHaveLength(1)
  })

  it('shows the saved answer of a new chat that finished while the user was away', async () => {
    renderChat('/ask')
    await sidebarLists('a')

    const first = await askAndGetStream('Brand new question')
    const created = conversation('n', 'Brand new chat')
    conversations.unshift(created)
    first.emit({ type: 'session', sessionId: 's2' }, '1-0')
    first.emit({ type: 'conversation', conversation: created }, '2-0')
    first.emit({ type: 'delta', text: 'Working' }, '3-0')
    await sidebarLists('n')

    openConversation('b')
    expect(await screen.findByText('Other answer')).toBeInTheDocument()
    // Meanwhile the server finished and saved the answer.
    details.n = { ...created, messages: [userMessage('n1', 'Brand new question'), assistantMessage('n2', 'The complete answer')] }

    openConversation('n')
    expect(await screen.findByText('The complete answer')).toBeInTheDocument()
    expect(screen.getByText('Brand new question')).toBeInTheDocument()
  })
})

describe('ChatView — Stop, then ask again', PAGE_TEST, () => {
  async function startAndStop() {
    renderChat('/ask/a')
    await sidebarLists('a')
    const first = await askAndGetStream('First question')
    first.emit({ type: 'session', sessionId: 's1' }, '1-0')
    first.emit({ type: 'conversation', conversation: conversation('a', 'Alpha') }, '2-0')
    first.emit({ type: 'delta', text: 'Partial' }, '3-0')
    await screen.findByText('Partial')

    fireEvent.click(screen.getByLabelText('Stop the answer'))
    expect(chatService.cancel).toHaveBeenCalledWith('s1')
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'Second question' } })
    // The server saves the partial answer as a stopped turn.
    details.a.messages = [userMessage('a1', 'First question'), assistantMessage('a2', 'Partial', 'stopped')]
    return first
  }

  it('keeps Send disabled until the stream confirms with cancelled, then keeps the stopped turn', async () => {
    const first = await startAndStop()
    expect(sendButton()).toBeDisabled()

    first.emit({ type: 'cancelled', message: 'The answer was stopped.' }, '4-0')
    await act(async () => first.finish())
    await waitFor(() => expect(sendButton()).toBeEnabled())

    fireEvent.click(sendButton())
    await waitFor(() => expect(askStreams()).toHaveLength(2))
    expect(await screen.findByText('Second question')).toBeInTheDocument()
    expect(screen.getByText('First question')).toBeInTheDocument()
    expect(screen.getByText('Partial')).toBeInTheDocument()
  })

  it(`re-enables Send after ${STOP_GRACE_MS / 1000} s without confirmation and still keeps the stopped turn`, async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await startAndStop()
    expect(sendButton()).toBeDisabled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STOP_GRACE_MS)
    })
    expect(sendButton()).toBeEnabled()

    fireEvent.click(sendButton())
    await waitFor(() => expect(askStreams()).toHaveLength(2))
    // Asking again closes the old stream without its history refresh: the saved copy is fetched first.
    expect(await screen.findByText('Second question')).toBeInTheDocument()
    expect(screen.getByText('First question')).toBeInTheDocument()
    expect(screen.getByText('Partial')).toBeInTheDocument()
  })
})

describe('ChatView — completion announcement', PAGE_TEST, () => {
  const announcement = () => screen.getByTestId('answer-announcement')

  async function startTurn() {
    renderChat('/ask/a')
    await sidebarLists('a')
    const stream = await askAndGetStream('First question')
    stream.emit({ type: 'session', sessionId: 's1' }, '1-0')
    stream.emit({ type: 'conversation', conversation: conversation('a', 'Alpha') }, '2-0')
    return stream
  }

  it('stays silent while the answer streams, then says "Answer ready" once; the streaming text is not a live region', async () => {
    const stream = await startTurn()
    stream.emit({ type: 'delta', text: 'Partial' }, '3-0')
    await screen.findByText('Partial')
    expect(announcement()).toHaveTextContent('')
    expect(announcement()).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByTestId('assistant-message')).not.toHaveAttribute('aria-live')

    stream.emit(
      { type: 'done', answer: { question: 'First question', answer: 'Partial answer.', grounded: true, mode: 'llm', model: 'm', sources: [], skippedBooks: [] } },
      '4-0',
    )
    await waitFor(() => expect(announcement()).toHaveTextContent('Answer ready'))
  })

  it('says "Answer stopped" when the turn is stopped', async () => {
    const stream = await startTurn()
    stream.emit({ type: 'delta', text: 'Partial' }, '3-0')
    await screen.findByText('Partial')
    fireEvent.click(screen.getByLabelText('Stop the answer'))
    stream.emit({ type: 'cancelled', message: 'The answer was stopped.' }, '4-0')
    await waitFor(() => expect(announcement()).toHaveTextContent('Answer stopped'))
  })

  it('leaves a failure to the answer alert: the status region stays silent', async () => {
    const stream = await startTurn()
    stream.emit({ type: 'error', error: { message: 'The model is unavailable.' } } as never, '3-0')
    expect(await screen.findByRole('alert')).toHaveTextContent('The model is unavailable.')
    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(announcement()).toHaveTextContent('')
  })
})

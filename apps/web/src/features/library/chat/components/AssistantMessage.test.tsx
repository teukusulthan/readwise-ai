import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { IAnswerSource } from '@/features/library/chat/types/chat.types'
import type { IBook } from '@/features/library/types/book.types'
import { AssistantMessage, type IAssistantView } from './AssistantMessage'

const source = (n: number, cited: boolean): IAnswerSource => ({
  n,
  bookId: `book-${n}`,
  bookTitle: `Book ${n}`,
  headings: ['Chapter 1', 'Origins'],
  pageStart: 4,
  pageEnd: 5,
  score: 0.71,
  text: `Passage ${n} text`,
  cited,
})

const message = (overrides: Partial<IAssistantView>): IAssistantView => ({
  id: 'm1',
  content: 'Frank Herbert wrote it [1].',
  mode: 'llm',
  grounded: true,
  sources: [source(1, true), source(2, false)],
  skippedBooks: [],
  model: 'test-model',
  error: null,
  ...overrides,
})

const openSources = () => fireEvent.click(screen.getByRole('button', { name: /2 sources/ }))

describe('AssistantMessage', () => {
  it('shows a grounded answer without a warning banner; sources are collapsed behind a counter', () => {
    render(<AssistantMessage message={message({})} />)

    expect(screen.queryByTestId('ungrounded-banner')).not.toBeInTheDocument()
    expect(screen.getByTestId('answer-text')).toHaveTextContent('Frank Herbert wrote it 1.')
    expect(screen.getByRole('button', { name: '2 sources, 1 cited' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)

    openSources()
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveAttribute('data-cited', 'true')
    expect(items[1]).toHaveAttribute('data-cited', 'false')
    expect(items[0]).toHaveAttribute('id', 'msg-m1-source-1')
    expect(screen.getAllByText(/Chapter 1 › Origins — pp\. 4–5/)).toHaveLength(2)
  })

  it('opens the sources and expands the cited passage when its chip is clicked', () => {
    render(<AssistantMessage message={message({ content: 'Built in 1847 [2].' })} />)

    fireEvent.click(screen.getByRole('button', { name: 'Show source 2' }))
    expect(screen.getByText('Passage 2 text')).toBeInTheDocument()
  })

  it('explains insufficient context instead of presenting an answer as grounded', () => {
    render(<AssistantMessage message={message({ mode: 'insufficient_context', grounded: false, content: "I couldn't find enough information." })} />)

    expect(screen.getByTestId('ungrounded-banner')).toHaveTextContent('Not enough information in the books')
  })

  it('shows the retrieval-only notice with every passage open', () => {
    render(<AssistantMessage message={message({ mode: 'retrieval_only', grounded: false, model: null, sources: [source(1, false)] })} />)

    expect(screen.getByTestId('ungrounded-banner')).toHaveTextContent('No language model configured')
    expect(screen.getByText('Passage 1 text')).toBeInTheDocument()
  })

  it('warns when an LLM answer cites nothing', () => {
    render(<AssistantMessage message={message({ grounded: false, sources: [source(1, false)] })} />)

    expect(screen.getByTestId('ungrounded-banner')).toHaveTextContent('Answer without citations')
  })

  it('renders model output as text, never as HTML', () => {
    render(<AssistantMessage message={message({ content: '<img src=x onerror=alert(1)> [1]' })} />)

    expect(screen.getByTestId('answer-text')).toHaveTextContent('<img src=x onerror=alert(1)>')
    expect(document.querySelector('img[src="x"]')).toBeNull()
  })

  it('lists books that could not be searched', () => {
    render(<AssistantMessage message={message({ skippedBooks: [{ id: 'b9', title: 'Draft', reason: 'not_indexed:processing' }] })} />)

    expect(screen.getByRole('note')).toHaveTextContent('Draft (still being indexed)')
  })

  it('keeps unknown citation numbers as plain text', () => {
    render(<AssistantMessage message={message({ content: 'Odd marker [9].' })} />)

    expect(screen.queryByRole('button', { name: 'Show source 9' })).not.toBeInTheDocument()
    expect(screen.getByTestId('answer-text')).toHaveTextContent('Odd marker [9].')
  })

  it('shows progress and no grounding banner while streaming', () => {
    render(<AssistantMessage message={message({ content: '', grounded: false, mode: null })} phase="generating" />)

    expect(screen.getByTestId('answer-progress')).toHaveTextContent('writing an answer')
    expect(screen.queryByTestId('ungrounded-banner')).not.toBeInTheDocument()
  })

  it('shows a failed answer with its error and keeps the sources', () => {
    render(<AssistantMessage message={message({ content: '', mode: 'error', error: 'The language model is rate-limited right now.' })} />)

    expect(screen.getByRole('alert')).toHaveTextContent('rate-limited')
    openSources()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })

  it('marks a stopped answer and keeps its partial text', () => {
    render(<AssistantMessage message={message({ content: 'The lifeboat', mode: 'stopped', grounded: false, sources: [] })} />)

    expect(screen.getByTestId('answer-text')).toHaveTextContent('The lifeboat')
    expect(screen.getByText('You stopped this answer.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it("shows the general-knowledge part in its own labeled box, without citation chips", () => {
    render(<AssistantMessage message={message({ content: "Built in 1847 [1].\n\nGENERAL KNOWLEDGE:\n\nLighthouses use Fresnel lenses [2]." })} />)

    expect(screen.getByTestId("answer-text")).toHaveTextContent("Built in 1847 1.")
    const general = screen.getByTestId("general-knowledge")
    expect(general).toHaveTextContent("General knowledge · not from your books")
    expect(general).toHaveTextContent("Lighthouses use Fresnel lenses [2].")
    expect(general.querySelector("button")).toBeNull()
    expect(screen.queryByTestId("ungrounded-banner")).not.toBeInTheDocument()
  })

  it("explains a general-knowledge-only answer with an info banner, not a warning", () => {
    render(<AssistantMessage message={message({ mode: "general_knowledge", grounded: false, sources: [], content: "GENERAL KNOWLEDGE:\nYour books do not cover this. Atomic Habits argues..." })} />)

    const banner = screen.getByTestId("ungrounded-banner")
    expect(banner).toHaveTextContent("Not found in your books")
    expect(banner).toHaveAttribute("data-tone", "info")
  })

  it("renders bullet lines as a list", () => {
    render(<AssistantMessage message={message({ content: "Three ideas:\n- Choose what to care about [1]\n- Take responsibility [2]" })} />)

    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(["Choose what to care about 1", "Take responsibility 2"])
  })

  it("shows cover cards of the cited books, linking to their pages", () => {
    const catalog = new Map<string, IBook>([["book-1", { id: "book-1", title: "Book 1", authors: ["H. G. Wells"], publishedYear: 1895, coverUrl: "https://covers.example/1.jpg" } as IBook]])
    render(
      <MemoryRouter>
        <AssistantMessage message={message({})} booksById={catalog} />
      </MemoryRouter>,
    )

    const cards = within(screen.getByTestId("cited-books")).getAllByRole("link")
    expect(cards).toHaveLength(1)                                  // book-2 is retrieved but not cited
    expect(cards[0]).toHaveAttribute("href", "/books/book-1")
    expect(cards[0]).toHaveTextContent("Book 1H. G. Wells · 18951 passage cited")
    expect(within(cards[0]).getByRole("img")).toHaveAttribute("src", "https://covers.example/1.jpg")
  })

  it("shows no cover cards when the answer cites nothing (e.g. general knowledge only)", () => {
    render(
      <MemoryRouter>
        <AssistantMessage message={message({ mode: "general_knowledge", grounded: false, content: "GENERAL KNOWLEDGE:\nx", sources: [source(1, false)] })} booksById={new Map()} />
      </MemoryRouter>,
    )
    expect(screen.queryByTestId("cited-books")).not.toBeInTheDocument()
  })

  it("still shows a cited book that is missing from the catalog, with a placeholder cover", () => {
    render(
      <MemoryRouter>
        <AssistantMessage message={message({})} booksById={new Map()} />
      </MemoryRouter>,
    )
    const card = within(screen.getByTestId("cited-books")).getByRole("link")
    expect(card).toHaveTextContent("Book 1")
    expect(within(card).getByRole("img", { name: "No cover for Book 1" })).toBeInTheDocument()
  })
})

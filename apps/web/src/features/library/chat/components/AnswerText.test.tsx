import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AnswerText } from './AnswerText'

const SOURCES: ReadonlySet<number> = new Set([1, 2])

function renderAnswer(text: string, extra: Partial<Parameters<typeof AnswerText>[0]> = {}) {
  const onCite = vi.fn()
  const view = render(<AnswerText text={text} sourceNumbers={SOURCES} activeSource={null} streaming={false} onCite={onCite} {...extra} />)
  return { onCite, ...view }
}

describe('AnswerText — Markdown', () => {
  it('renders bold, italics, headings, lists, code and blockquotes as elements', () => {
    const { container } = renderAnswer(
      ['## Title', '', 'Some **bold** and *italic* text with `inline`.', '', '- one', '- two', '', '1. first', '2. second', '', '> quoted', '', '```', 'code block', '```'].join('\n'),
    )
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument()
    expect(container.querySelector('strong')).toHaveTextContent('bold')
    expect(container.querySelector('em')).toHaveTextContent('italic')
    expect(container.querySelector('p code')).toHaveTextContent('inline')
    expect(container.querySelectorAll('ul > li')).toHaveLength(2)
    expect(container.querySelectorAll('ol > li')).toHaveLength(2)
    expect(container.querySelector('blockquote')).toHaveTextContent('quoted')
    expect(container.querySelector('pre')).toHaveTextContent('code block')
  })

  it('renders GFM tables inside a horizontally scrollable wrapper', () => {
    const { container } = renderAnswer('| Name | Year |\n| --- | --- |\n| Dune | 1965 |')
    const table = screen.getByRole('table')
    expect(within(table).getByRole('columnheader', { name: 'Year' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: 'Dune' })).toBeInTheDocument()
    expect(container.querySelector('.overflow-x-auto')).toContainElement(table)
  })

  it('keeps clickable citation chips inside paragraphs, list items, table cells and bold text', () => {
    const { onCite, container } = renderAnswer(
      ['Paragraph [1].', '', '- item **strong [2]**', '- plain [2][1]', '', '| A |', '| --- |', '| cell [1] |'].join('\n'),
    )
    expect(container.querySelectorAll('[data-citation]')).toHaveLength(5)
    const inList = container.querySelectorAll('li [data-citation]')
    expect(inList).toHaveLength(3)
    expect(container.querySelector('td [data-citation="1"]')).not.toBeNull()
    expect(container.querySelector('strong [data-citation="2"]')).not.toBeNull()
    fireEvent.click(inList[1])
    expect(onCite).toHaveBeenCalledWith(2)
    expect(screen.getByTestId('answer-text')).toHaveTextContent('item strong 2')
  })

  it('leaves markers for unknown sources as literal text', () => {
    renderAnswer('See [7].')
    expect(screen.getByTestId('answer-text')).toHaveTextContent('See [7].')
    expect(document.querySelector('[data-citation]')).toBeNull()
  })

  it('does not render raw HTML: script and tags are dropped, never injected', () => {
    const { container } = renderAnswer('Hello <script>window.__pwned = true</script> <img src=x onerror="window.__pwned = true"> <b>raw</b> world')
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
    expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined()
  })

  it('opens links in a new tab safely and blocks javascript: URLs', () => {
    renderAnswer('[Docs](https://example.com/page) and [bad](javascript:alert(1))')
    const good = screen.getByRole('link', { name: 'Docs' })
    expect(good).toHaveAttribute('href', 'https://example.com/page')
    expect(good).toHaveAttribute('target', '_blank')
    expect(good).toHaveAttribute('rel', 'noopener noreferrer')
    const bad = screen.queryByRole('link', { name: 'bad' })
    expect(bad?.getAttribute('href') ?? '').not.toMatch(/javascript:/i)
  })

  it('does not load remote images; shows the alt text', () => {
    const { container } = renderAnswer('![a cover](https://example.com/c.png)')
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByTestId('answer-text')).toHaveTextContent('a cover')
  })

  it('renders partial Markdown while streaming without crashing, with the caret inline', () => {
    const { container } = renderAnswer('A **bold start [1] and a table:\n\n| A | B |\n| --- ', { streaming: true })
    expect(screen.getByTestId('answer-text')).toHaveTextContent('A **bold start 1 and a table:')
    expect(container.querySelectorAll('.animate-caret').length).toBeLessThanOrEqual(1)
  })

  it('puts the streaming caret at the end of the last paragraph', () => {
    const { container } = renderAnswer('First.\n\nSecond so far', { streaming: true })
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs[0].querySelector('.animate-caret')).toBeNull()
    expect(paragraphs[1].querySelector('.animate-caret')).not.toBeNull()
  })
})

describe('AnswerText — general knowledge', () => {
  it('shows the labeled box after the exact heading line, without citation chips', () => {
    renderAnswer('From the book [1].\n\nGENERAL KNOWLEDGE:\n\nOutside fact [1].')
    const box = screen.getByTestId('general-knowledge')
    expect(box).toHaveTextContent('Outside fact [1].')
    expect(box.querySelector('[data-citation]')).toBeNull()
  })

  it('does not split on a paragraph that merely starts with "General knowledge of"', () => {
    renderAnswer('From the book [1].\n\nGeneral knowledge of the period was limited [2].')
    expect(screen.queryByTestId('general-knowledge')).toBeNull()
    expect(screen.getByTestId('answer-text')).toHaveTextContent('General knowledge of the period was limited 2.')
  })
})

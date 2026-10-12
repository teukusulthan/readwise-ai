import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PerfectScrollArea } from './PerfectScrollArea'

describe('PerfectScrollArea', () => {
  it('renders children inside a perfect-scrollbar container', () => {
    render(
      <PerfectScrollArea className="h-full">
        <p>Scrollable content</p>
      </PerfectScrollArea>,
    )

    const content = screen.getByText('Scrollable content')
    const container = content.parentElement as HTMLElement
    expect(container).toHaveClass('scrollbar-container', 'perfect-scroll-area', 'min-h-0', 'h-full')
  })

  it('forwards the ref to the scroll container element', () => {
    const ref = createRef<HTMLElement>()
    render(
      <PerfectScrollArea ref={ref}>
        <p>Content</p>
      </PerfectScrollArea>,
    )

    expect(ref.current).toBeInstanceOf(HTMLElement)
    expect(ref.current).toHaveClass('perfect-scroll-area')
  })
})

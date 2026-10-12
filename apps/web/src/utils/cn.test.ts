import { describe, expect, it } from 'vitest'

import { cn } from './cn'

describe('cn', () => {
  it('keeps a text color next to a design-token font size', () => {
    expect(cn('text-font-on-accent', 'text-body-md')).toBe('text-font-on-accent text-body-md')
  })

  it('still lets a later font size override an earlier one', () => {
    expect(cn('text-body-md', 'text-body-sm')).toBe('text-body-sm')
  })

  it('still lets a later text color override an earlier one', () => {
    expect(cn('text-font-primary', 'text-primary-bold')).toBe('text-primary-bold')
  })
})

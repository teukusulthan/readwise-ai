import { describe, expect, it } from 'vitest'

import { loginPathFor, safeNextPath } from './auth-redirect'

describe('auth redirects', () => {
  it('remembers the page to return to', () => {
    expect(loginPathFor('/ask/abc?x=1')).toBe('/login?next=%2Fask%2Fabc%3Fx%3D1')
    expect(loginPathFor('/login')).toBe('/login')
    expect(loginPathFor('/register?x=1')).toBe('/login')
  })

  it('only returns to paths inside the app', () => {
    expect(safeNextPath('/search?q=whales')).toBe('/search?q=whales')
    for (const unsafe of [
      null,
      '',
      'https://evil.test',
      '//evil.test',
      '/\\evil.test',
      '/\t/evil.test',
      '/\n/evil.test',
      '/books\\..\\//evil.test',
      'books',
      'javascript:alert(1)',
      '/login',
      '/login?next=https://evil.test',
    ]) {
      expect(safeNextPath(unsafe)).toBe('/books')
    }
  })
})

// Registers jest-dom matchers (toBeInTheDocument, ...) on vitest's `expect`.
// https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Testing Library only auto-unmounts when vitest globals are enabled; they are not,
// so unmount explicitly or renders from earlier tests leak into later queries.
afterEach(() => {
  cleanup()
})

import { type ClassValue, clsx } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

/**
 * tailwind-merge must know the design-token type scale (`text-body-md`, `text-h5`, …).
 * Otherwise it treats them as text *colors* and drops a real color class such as
 * `text-font-on-accent` when both appear in one `cn()` call.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': [
        { text: ['display', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'body-lg', 'body-md', 'body-sm', 'label-lg', 'label-md', 'label-sm'] },
      ],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

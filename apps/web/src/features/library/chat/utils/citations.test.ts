import { describe, expect, it } from 'vitest'

import { segmentCitations, splitGeneralKnowledge } from './citations'

describe('segmentCitations', () => {
  it('turns known [n] markers into citation segments', () => {
    expect(segmentCitations('Built in 1847 [1][2].', new Set([1, 2]))).toEqual([
      { type: 'text', text: 'Built in 1847 ' },
      { type: 'cite', n: 1 },
      { type: 'cite', n: 2 },
      { type: 'text', text: '.' },
    ])
  })

  it('leaves unknown numbers and partial markers as text', () => {
    expect(segmentCitations('See [7] and [1', new Set([1]))).toEqual([{ type: 'text', text: 'See [7] and [1' }])
  })
})

describe('splitGeneralKnowledge', () => {
  it('separates the general-knowledge section from the book part', () => {
    expect(splitGeneralKnowledge('Book fact [1].\n\nGENERAL KNOWLEDGE:\n\nOutside fact.')).toEqual(['Book fact [1].\n\n', '\n\nOutside fact.'])
  })

  it('tolerates Markdown decoration and lower case around the heading line', () => {
    expect(splitGeneralKnowledge('A [1].\n**General knowledge:**\nClear wrote it.')[1]).toBe('\nClear wrote it.')
    expect(splitGeneralKnowledge('A [1].\n## general knowledge:\nClear wrote it.')[1]).toBe('\nClear wrote it.')
    expect(splitGeneralKnowledge('A [1].\n**General knowledge**:\nClear wrote it.')[1]).toBe('\nClear wrote it.')
  })

  it('keeps text after the colon on the heading line in the general part', () => {
    expect(splitGeneralKnowledge('A [1].\n**General knowledge:** Clear wrote it.')).toEqual(['A [1].\n', 'Clear wrote it.'])
    expect(splitGeneralKnowledge('A [1].\nGeneral knowledge: Clear wrote it.')[1]).toBe('Clear wrote it.')
  })

  it('does not split on ordinary sentences that merely start with the words', () => {
    expect(splitGeneralKnowledge('General knowledge of history helps. It is [1].')).toEqual(['General knowledge of history helps. It is [1].', null])
    expect(splitGeneralKnowledge('A [1].\n\nGeneral knowledge of the era says more.')[1]).toBeNull()
    expect(splitGeneralKnowledge('A [1].\nGeneral knowledge\nbut no colon.')[1]).toBeNull()
  })

  it('returns null when there is no section, and an empty book part for general-only answers', () => {
    expect(splitGeneralKnowledge('Only books [2].')).toEqual(['Only books [2].', null])
    expect(splitGeneralKnowledge('GENERAL KNOWLEDGE:\nYour books do not cover this.')).toEqual(['', '\nYour books do not cover this.'])
  })
})

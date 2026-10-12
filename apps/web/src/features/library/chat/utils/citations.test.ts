import { describe, expect, it } from 'vitest'

import { segmentCitations, splitGeneralKnowledge, splitParagraphs, toBlocks } from './citations'

describe('splitParagraphs', () => {
  it('treats every line break as a paragraph break', () => {
    expect(splitParagraphs('One.\nTwo.\n\n\nThree.\r\n\r\nFour.\n  \n')).toEqual(['One.', 'Two.', 'Three.', 'Four.'])
  })
})

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

  it('tolerates Markdown, lower case and text on the heading line', () => {
    expect(splitGeneralKnowledge('A [1].\n**General knowledge:** Clear wrote it.')[1]).toBe('Clear wrote it.')
  })

  it('returns null when there is no section, and an empty book part for general-only answers', () => {
    expect(splitGeneralKnowledge('Only books [2].')).toEqual(['Only books [2].', null])
    expect(splitGeneralKnowledge('GENERAL KNOWLEDGE:\nYour books do not cover this.')).toEqual(['', '\nYour books do not cover this.'])
  })
})

describe('toBlocks', () => {
  it('groups bullet and numbered lines into lists', () => {
    expect(toBlocks(['Intro.', '- one [1]', '- two', '1. first', '2) second', 'Outro.'])).toEqual([
      { type: 'p', text: 'Intro.' },
      { type: 'ul', items: ['one [1]', 'two'] },
      { type: 'ol', items: ['first', 'second'] },
      { type: 'p', text: 'Outro.' },
    ])
  })
})

import type { TAnswerMode } from '@/features/library/chat/types/chat.types'

export interface IAnswerModeMeta {
  title: string
  description: string
  icon: string
  /** info = expected behaviour worth knowing; warning = treat the answer with caution */
  tone: 'info' | 'warning'
}

/** Explanations shown when an answer is NOT grounded in book text (mode !== 'llm' or no citations). */
export const UNGROUNDED_MODE_META: Record<Exclude<TAnswerMode, 'llm'>, IAnswerModeMeta> = {
  general_knowledge: {
    title: 'Not found in your books',
    description: 'Nothing in the indexed books answers this, so the answer comes from the model’s general knowledge. It has no citations — check important facts.',
    icon: 'globe-hemisphere-west',
    tone: 'info',
  },
  insufficient_context: {
    title: 'Not enough information in the books',
    description: 'Relevant passages were found, but they do not contain enough to answer. No answer was invented.',
    icon: 'question',
    tone: 'warning',
  },
  no_context: {
    title: 'No relevant passages found',
    description: 'Nothing in the selected indexed books matched this question closely enough.',
    icon: 'magnifying-glass-minus',
    tone: 'warning',
  },
  no_indexed_books: {
    title: 'No indexed books to search',
    description: 'Upload a PDF and wait until its status is “Indexed (searchable)”.',
    icon: 'books',
    tone: 'warning',
  },
  retrieval_only: {
    title: 'No language model configured',
    description: 'The server has no LLM key yet, so no answer was generated. The passages below are the closest matches.',
    icon: 'plug',
    tone: 'info',
  },
}

export const UNCITED_ANSWER_META: IAnswerModeMeta = {
  title: 'Answer without citations',
  description: 'The model did not cite any passage, so this answer may not be grounded in the books. Treat it with caution.',
  icon: 'warning',
  tone: 'warning',
}

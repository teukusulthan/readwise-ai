import { Children, createContext, Fragment, useContext, useMemo, type ReactNode } from 'react'
import ReactMarkdown, { type Components, type ExtraProps } from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { segmentCitations } from '@/features/library/chat/utils/citations'
import { cn } from '@/utils/cn'

interface AnswerMarkdownProps {
  text: string
  /** Source numbers that may become clickable chips; other `[n]` markers stay literal text. */
  sourceNumbers: ReadonlySet<number>
  activeSource: number | null
  onCite: (n: number) => void
  /** Shown at the very end of the text while the answer is still being written. */
  caret?: ReactNode
}

const REMARK_PLUGINS = [remarkGfm]

interface IMarkdownContext {
  sourceNumbers: ReadonlySet<number>
  activeSource: number | null
  onCite: (n: number) => void
  caret: ReactNode
  /** Length of the text without trailing whitespace: the block that reaches it holds the caret. */
  textEnd: number
}

/**
 * react-markdown remounts every element whose component function changes identity, so the
 * overrides below are module-level constants and read what changes (sources, active chip,
 * caret) from this context.
 */
const MarkdownContext = createContext<IMarkdownContext>({ sourceNumbers: new Set(), activeSource: null, onCite: () => {}, caret: null, textEnd: 0 })

function CitationChip({ n }: { n: number }) {
  const { activeSource, onCite } = useContext(MarkdownContext)
  return (
    <button
      type="button"
      onClick={() => onCite(n)}
      aria-label={`Show source ${n}`}
      data-citation={n}
      className={cn(
        'mx-0.5 inline-flex h-6 min-w-6 -translate-y-px items-center justify-center rounded-md px-1.5 align-middle text-label-md font-semibold leading-none transition-[background-color,color,scale,box-shadow] duration-200 ease-spring hover:scale-110 hover:shadow-sm active:scale-95 active:duration-75',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        activeSource === n ? 'bg-primary text-font-on-accent' : 'bg-primary-light text-primary-bold hover:bg-primary-soft',
      )}
    >
      {n}
    </button>
  )
}

/** Turns `[n]` markers inside plain-text children into chips; elements (strong, em, ...) get their own override. */
function Cited({ children }: { children?: ReactNode }) {
  const { sourceNumbers } = useContext(MarkdownContext)
  return (
    <>
      {Children.map(children, (child) =>
        typeof child === 'string'
          ? segmentCitations(child, sourceNumbers).map((segment, i) =>
              segment.type === 'text' ? <Fragment key={i}>{segment.text}</Fragment> : <CitationChip key={i} n={segment.n} />,
            )
          : child,
      )}
    </>
  )
}

/** The streaming caret, inline at the end of the block that holds the end of the text. */
function Tail({ node }: { node: ExtraProps['node'] }) {
  const { caret, textEnd } = useContext(MarkdownContext)
  if (!caret || (node?.position?.end.offset ?? -1) < textEnd) return null
  // A parent item/cell that wraps a deeper block leaves the caret to that block.
  if (node?.children.some((child) => child.type === 'element' && ['p', 'ul', 'ol'].includes(child.tagName))) return null
  return <>{caret}</>
}

const COMPONENTS: Components = {
  p: ({ node, children }) => (
    <p className="whitespace-pre-line">
      <Cited>{children}</Cited>
      <Tail node={node} />
    </p>
  ),
  li: ({ node, children }) => (
    <li className="pl-1 marker:text-font-placeholder">
      <Cited>{children}</Cited>
      <Tail node={node} />
    </li>
  ),
  ul: ({ children, className }) => (
    <ul className={cn('flex flex-col gap-1.5 pl-6', className?.includes('contains-task-list') ? 'list-none pl-1' : 'list-disc')}>{children}</ul>
  ),
  ol: ({ children, start }) => (
    <ol start={start} className="flex list-decimal flex-col gap-1.5 pl-6">
      {children}
    </ol>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold">
      <Cited>{children}</Cited>
    </strong>
  ),
  em: ({ children }) => (
    <em>
      <Cited>{children}</Cited>
    </em>
  ),
  del: ({ children }) => (
    <del>
      <Cited>{children}</Cited>
    </del>
  ),
  h1: ({ children }) => (
    <h3 className="font-serif text-h6 font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h3>
  ),
  h2: ({ children }) => (
    <h3 className="font-serif text-h6 font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h3>
  ),
  h3: ({ children }) => (
    <h4 className="font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h4>
  ),
  h4: ({ children }) => (
    <h4 className="font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h4>
  ),
  h5: ({ children }) => (
    <h5 className="font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h5>
  ),
  h6: ({ children }) => (
    <h5 className="font-semibold text-font-primary">
      <Cited>{children}</Cited>
    </h5>
  ),
  blockquote: ({ children }) => <blockquote className="border-l-2 border-border-secondary pl-4 text-font-secondary">{children}</blockquote>,
  hr: () => <hr className="border-border-primary" />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-primary-bold underline underline-offset-2 hover:text-primary">
      <Cited>{children}</Cited>
    </a>
  ),
  // Remote images would load on render (tracking, hotlinking); show the description instead.
  img: ({ alt }) => (alt ? <span>{alt}</span> : null),
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-lg border border-border-primary bg-background-secondary p-3 text-body-sm leading-normal">{children}</pre>
  ),
  code: ({ children, className }) => (
    <code className={cn('font-mono', className ? 'text-font-primary' : 'rounded bg-background-secondary px-1 py-0.5 text-[0.9em]')}>{children}</code>
  ),
  table: ({ children }) => (
    <div className="max-w-full overflow-x-auto rounded-lg border border-border-primary" tabIndex={0} role="region" aria-label="Table">
      <table className="w-full border-collapse text-left text-body-md">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-background-secondary">{children}</thead>,
  th: ({ children, style }) => (
    <th style={style} className="border-b border-border-primary px-3 py-2 font-semibold whitespace-nowrap">
      <Cited>{children}</Cited>
    </th>
  ),
  td: ({ node, children, style }) => (
    <td style={style} className="border-b border-border-primary px-3 py-2 align-top">
      <Cited>{children}</Cited>
      <Tail node={node} />
    </td>
  ),
  input: ({ checked }) => <input type="checkbox" checked={checked} disabled readOnly className="mr-2 align-middle" />,
}

/**
 * Renders the model's answer as Markdown (GFM) with `[n]` citation chips inside text.
 * Safe by construction: no `rehype-raw`, so raw HTML is dropped; react-markdown's default URL
 * transform blocks `javascript:` links; images are replaced by their alt text (no remote loads).
 */
export function AnswerMarkdown({ text, sourceNumbers, activeSource, onCite, caret }: AnswerMarkdownProps) {
  const textEnd = text.trimEnd().length
  const context = useMemo(() => ({ sourceNumbers, activeSource, onCite, caret, textEnd }), [sourceNumbers, activeSource, onCite, caret, textEnd])
  return (
    <MarkdownContext.Provider value={context}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={COMPONENTS}>
        {text}
      </ReactMarkdown>
    </MarkdownContext.Provider>
  )
}

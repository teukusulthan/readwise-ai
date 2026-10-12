/** The search page keeps its state in the URL: `?q=<query>` and, when scoped, `?books=<id>,<id>`. */
export interface ISearchParams {
  query: string
  bookIds: string[]
}

export function readSearchParams(params: URLSearchParams): ISearchParams {
  const bookIds = (params.get('books') ?? '').split(',').map((id) => id.trim()).filter(Boolean)
  return { query: (params.get('q') ?? '').trim(), bookIds: [...new Set(bookIds)] }
}

export function buildSearchParams({ query, bookIds }: ISearchParams): URLSearchParams {
  const params = new URLSearchParams()
  if (query) params.set('q', query)
  if (bookIds.length) params.set('books', bookIds.join(','))
  return params
}

/** The chat reads repeated `bookId` params as its preselected books. */
export function askAboutBookPath(bookId: string): string {
  return `/ask?${new URLSearchParams({ bookId })}`
}

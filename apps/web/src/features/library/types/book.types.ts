/** Mirrors the backend book object (apps/backend/service/book.py → to_api). */

export type TIngestionStatus = 'none' | 'queued' | 'processing' | 'indexed' | 'failed'

export type TMetadataSource = 'manual' | 'openlibrary' | 'upload'

export interface IBookDocument {
  fileName: string
  sizeBytes: number
  pageCount: number | null
}

export interface IBookIngestion {
  status: TIngestionStatus
  error: string | null
  chunkCount: number
  embeddingModel: string | null
  indexedAt: string | null
}

export interface IBook {
  id: string
  title: string
  authors: string[]
  description: string | null
  isbn: string | null
  coverUrl: string | null
  publisher: string | null
  publishedYear: number | null
  language: string | null
  subjects: string[]
  metadataSource: TMetadataSource
  hasDocument: boolean
  document: IBookDocument | null
  ingestion: IBookIngestion
  /** Only `true` when the full text is indexed — the one flag RAG features rely on. */
  searchable: boolean
  createdAt: string
  updatedAt: string
}

export type TBookOrderBy = 'createdAt' | 'title' | 'publishedYear' | 'updatedAt' | 'indexedAt'

export interface IBookListParams {
  search?: string
  status?: TIngestionStatus[]
  page: number
  size: number
  orderBy?: TBookOrderBy
  order?: 'asc' | 'desc'
}

export interface IBookCreatePayload {
  title: string
  authors: string[]
  description?: string
  isbn?: string
  coverUrl?: string
  publisher?: string
  publishedYear?: number
  language?: string
  subjects: string[]
}

export interface IBookUpdatePayload extends IBookCreatePayload {
  id: string
}

export interface IBookUploadPayload {
  file: File
  bookId?: string
  title?: string
}

/** Open Library candidate returned by /book/lookup. */
export interface IExternalBook {
  title: string
  authors: string[]
  isbn: string
  coverUrl: string | null
  publishedYear: number | null
  externalId: string | null
}

export interface IBookDeleteResult {
  id: string
  deleted: boolean
}

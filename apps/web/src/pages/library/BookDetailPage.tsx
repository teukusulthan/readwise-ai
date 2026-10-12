import { useParams } from 'react-router-dom'

import { BookDetailView } from '@/features/library/books/components/BookDetailView'

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>()
  return <BookDetailView bookId={id} />
}

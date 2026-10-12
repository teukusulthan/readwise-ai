import { Badge } from '@/components/ui/badge'
import { INGESTION_STATUS_META } from '@/features/library/constants/ingestion-status'
import type { TIngestionStatus } from '@/features/library/types/book.types'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface BookStatusBadgeProps {
  status: TIngestionStatus
  className?: string
}

/** Makes the metadata-only vs indexed distinction impossible to miss. */
export function BookStatusBadge({ status, className }: BookStatusBadgeProps) {
  const meta = INGESTION_STATUS_META[status]
  return (
    <Badge variant={meta.variant} className={cn('gap-1.5', className)} title={meta.description} data-status={status} data-cursor="help">
      {renderIcon({ icon: meta.icon, className: cn('text-[15px]', status === 'processing' && 'animate-spin') })}
      {meta.label}
    </Badge>
  )
}

import { z } from 'zod'

import { MAX_UPLOAD_MB } from '@/features/library/constants/catalog'

export const uploadSchema = z.object({
  file: z
    .custom<File | undefined>((value) => value === undefined || value instanceof File, 'Choose a file')
    .refine((file): file is File => file instanceof File, 'Choose a PDF file')
    .refine((file) => !file || file.name.toLowerCase().endsWith('.pdf'), 'Only .pdf files are supported')
    .refine((file) => !file || file.size <= MAX_UPLOAD_MB * 1024 * 1024, `The file must be ${MAX_UPLOAD_MB} MB or smaller`),
  title: z.string().max(500, 'Title must be 500 characters or fewer'),
})

export type TUploadFormValues = z.infer<typeof uploadSchema>

import { QueryClient } from '@tanstack/react-query'

/** Shared TanStack Query client — mounted once in `src/main.tsx`. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 10,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

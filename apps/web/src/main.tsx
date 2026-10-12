import './index.css'

import { QueryClientProvider } from '@tanstack/react-query'
import moment from 'moment-timezone'
import ReactDOM from 'react-dom/client'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { queryClient } from '@/config/query-client'
import { applyAppTheme } from '@/config/theme'
import RouteIndex from './routes'

import * as serviceWorkerRegistration from './pwa-register'
import reportWebVitals from './report-web-vitals'

moment.tz(Intl.DateTimeFormat().resolvedOptions().timeZone).format()
applyAppTheme()

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement)
root.render(
  <QueryClientProvider client={queryClient}>
    {/* One provider: moving between hinted controls shows the next tooltip instantly. */}
    <TooltipProvider delayDuration={350} skipDelayDuration={250}>
      <RouteIndex />
    </TooltipProvider>
    <Toaster />
  </QueryClientProvider>,
)

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://cra.link/PWA
serviceWorkerRegistration.register()

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals()

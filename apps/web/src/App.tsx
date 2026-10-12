import type { ReactElement } from 'react'
import { Badge } from '@/components/ui/badge'
import env from '@/config/env'

// ─── Constants ────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: 'ph-lightning',
    title: 'Vite + React 18',
    desc: 'Dev server instan lewat native ESM, HMR super cepat, TypeScript strict, path alias siap pakai.',
    accent: 'primary',
  },
  {
    icon: 'ph-paint-brush-broad',
    title: 'Fusion Design System',
    desc: 'Token-based dengan Tailwind v4 dan shadcn/ui. Dark mode, radius, shadow, dan typography terkurasi.',
    accent: 'secondary',
  },
  {
    icon: 'ph-database',
    title: 'Supabase Integration',
    desc: 'Auth JWT, Postgres, Storage, dan Realtime channel sudah terkonfigurasi penuh.',
    accent: 'tertiary',
  },
  {
    icon: 'ph-arrows-counter-clockwise',
    title: 'TanStack Query + Zustand + XState',
    desc: 'Server state via TanStack Query, UI state via Zustand, workflow state via XState v5 — separation of concern sempurna.',
    accent: 'quaternary',
  },
  {
    icon: 'ph-plug',
    title: 'Service Layer — api-factory',
    desc: 'apiRequests (get/post/put/patch/delete/upload) + createResourceService untuk CRUD standard. Satu import, semua method.',
    accent: 'quinary',
  },
  {
    icon: 'ph-funnel',
    title: 'Dynamic Filter System',
    desc: '6 tipe filter URL-driven — range, dependent, multi-select, date, slider, hingga widget-to-widget.',
    accent: 'primary',
  },
]

const STACK = [
  { label: 'React 18', accent: '#1278A8' },
  { label: 'TypeScript', accent: '#1278A8' },
  { label: 'Tailwind v4', accent: '#2EA38C' },
  { label: 'shadcn/ui', accent: '#2EA38C' },
  { label: 'Zustand', accent: '#FFB81F' },
  { label: 'TanStack Query', accent: '#FFB81F' },
  { label: 'Supabase', accent: '#696F7A' },
  { label: 'XState v5', accent: '#696F7A' },
  { label: 'FastAPI', accent: '#FF6433' },
  { label: 'Agno + FastMCP', accent: '#FF6433' },
]

const ACCENT_MAP: Record<string, { bg: string; border: string; text: string }> = {
  primary: { bg: 'bg-(--primary-light)', border: 'border-(--primary-soft)', text: 'text-(--primary-bold)' },
  secondary: { bg: 'bg-(--secondary-light)', border: 'border-(--secondary-soft)', text: 'text-(--secondary-bold)' },
  tertiary: { bg: 'bg-(--tertiary-light)', border: 'border-(--tertiary-soft)', text: 'text-(--tertiary-bold)' },
  quaternary: { bg: 'bg-(--quaternary-light)', border: 'border-(--quaternary-soft)', text: 'text-(--quaternary-bold)' },
  quinary: { bg: 'bg-(--quinary-light)', border: 'border-(--quinary-soft)', text: 'text-(--quinary-bold)' },
}

const AI_SKILLS = [
  { icon: 'ph-lightning', name: 'bootstrap-project', desc: 'Scaffold project baru dari template stack yang dipilih.' },
  { icon: 'ph-map-trifold', name: 'brief-builder', desc: 'Susun technical brief & spesifikasi dari kebutuhan klien.' },
  { icon: 'ph-palette', name: 'design-system-builder', desc: 'Generate design tokens, DESIGN.md, dan brand guideline lengkap.' },
  { icon: 'ph-code', name: 'html-to-react', desc: 'Konversi mockup HTML jadi feature React terstruktur.' },
  { icon: 'ph-scissors', name: 'html-ui-slicing', desc: 'Slicing UI dari desain ke komponen shadcn/Tailwind.' },
  { icon: 'ph-magnifying-glass', name: 'search-localdata', desc: 'Fuzzy search client-side di atas data lokal/mock.' },
  { icon: 'ph-flag-checkered', name: 'sprint-builder', desc: 'Rencanakan & jalankan sprint AI-driven per fitur.' },
  { icon: 'ph-database', name: 'supabase-init', desc: 'Bootstrap Supabase self-hosted lengkap dengan secrets.' },
  { icon: 'ph-compass', name: 'uiux', desc: 'Terapkan design token ke komponen web & mobile.' },
]

const CHANGELOG = [
  {
    version: 'v1.0.0',
    date: '10 Jun 2026',
    tag: 'stable',
    notes: ['Initial boilerplate release', 'Fusion design system + Tailwind v4', 'Report approval flow dengan XState v5', 'Mock data layer siap pakai'],
  },
  {
    version: 'v0.9.0',
    date: '01 Jun 2026',
    tag: 'beta',
    notes: ['Dynamic filter module', 'TanStack Query integration', 'Auth flow dengan JWT + HTTP-only cookie'],
  },
  { version: 'v0.8.0', date: '20 Mei 2026', tag: 'beta', notes: ['Vite setup', 'Sprint builder workflow', 'Zustand store pattern'] },
]

const TAG_VARIANT: Record<string, 'success' | 'warning' | 'info'> = {
  stable: 'success',
  beta: 'warning',
  alpha: 'info',
}

const TECH_RADAR = [
  { layer: 'Frontend', tech: 'React 18 + TypeScript', decision: 'Ekosistem terluas, DX terbaik, dukungan AI codegen sangat baik.', status: 'adopted' },
  {
    layer: 'Build',
    tech: 'Vite',
    decision: 'Native ESM dev server, HMR super cepat, ekosistem plugin luas, zero-config untuk sebagian besar kasus.',
    status: 'adopted',
  },
  { layer: 'Styling', tech: 'Tailwind v4 + shadcn', decision: 'Token-driven, headless behavior, tidak lock-in ke design tertentu.', status: 'adopted' },
  {
    layer: 'State',
    tech: 'Zustand + TanStack Q',
    decision: 'Zustand untuk UI/client state, TanStack Query untuk server cache — jangan campur keduanya.',
    status: 'adopted',
  },
  {
    layer: 'Workflow',
    tech: 'XState v5',
    decision: 'Approval flow punya transition rules — state machine lebih aman dari if/else + Zustand status string.',
    status: 'adopted',
  },
  {
    layer: 'Service',
    tech: 'api-factory + CRUD',
    decision: 'apiRequests sebagai base HTTP layer, createResourceService untuk CRUD standard — tidak perlu tulis ulang.',
    status: 'adopted',
  },
  { layer: 'Database', tech: 'Supabase', decision: 'Auth + Postgres + Storage + Realtime dalam satu platform, free tier cukup untuk MVP.', status: 'adopted' },
  { layer: 'Agent', tech: 'Agno + FastMCP', decision: 'Framework Python ringan untuk AI agent, native OpenRouter support.', status: 'trial' },
]

const STATUS_VARIANT: Record<string, 'success' | 'info'> = {
  adopted: 'success',
  trial: 'info',
}

const SPRINT_TASKS = [
  { id: 'RA-01', title: 'Report List & Filter', status: 'done', stack: 'web' },
  { id: 'RA-02', title: 'Approval State Machine', status: 'done', stack: 'web' },
  { id: 'RA-03', title: 'Welcome Page', status: 'done', stack: 'web' },
  { id: 'RA-04', title: 'Auth Guard', status: 'planned', stack: 'web' },
  { id: 'RA-05', title: 'Backend API', status: 'planned', stack: 'be' },
]

const TASK_STYLE: Record<string, { variant: 'success' | 'warning' | 'neutral'; label: string; icon: string }> = {
  done: { variant: 'success', label: 'Done', icon: 'ph-check-circle' },
  'in-progress': { variant: 'warning', label: 'In Progress', icon: 'ph-spinner' },
  planned: { variant: 'neutral', label: 'Planned', icon: 'ph-circle-dashed' },
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({
  badge,
  badgeVariant,
  title,
  sub,
}: {
  badge: string
  badgeVariant: 'info' | 'success' | 'warning' | 'neutral'
  title: string
  sub?: string
}) {
  return (
    <div className="mb-12 text-center">
      <Badge variant={badgeVariant} className="mb-3">
        {badge}
      </Badge>
      <h2 className="text-3xl font-bold text-(--text-color-primary)">{title}</h2>
      {sub && <p className="mt-3 text-(--text-color-secondary)">{sub}</p>}
    </div>
  )
}

function EnvIndicator() {
  const mode = env.app.mode
  const apiUrl = env.api.baseUrl

  const envColor: Record<string, string> = {
    production: '#2EA38C',
    staging: '#FFB81F',
    development: '#1278A8',
  }
  const color = envColor[mode] ?? envColor.development

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-1.5 rounded-xl border border-(--border-primary) bg-(--bg-secondary) px-4 py-3 shadow-lg text-xs">
      <div className="flex items-center gap-2 font-semibold text-(--text-color-primary)">
        <span className="ph ph-activity text-sm" style={{ color }} />
        Environment
      </div>
      <div className="flex items-center gap-2 text-(--text-color-secondary)">
        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="capitalize font-medium" style={{ color }}>
          {mode}
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-(--text-color-placeholder)">
        <span className="ph ph-link-simple" />
        <span className="max-w-[160px] truncate">{apiUrl}</span>
      </div>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

function App(): ReactElement {
  return (
    <div className="min-h-screen bg-(--bg-primary) overflow-x-hidden">
      {/* ── ENV INDICATOR (fixed) ────────────────────────── */}
      <EnvIndicator />

      {/* ── HERO ─────────────────────────────────────────── */}
      <section className="relative isolate overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[600px] rounded-full opacity-30 blur-3xl"
          style={{
            background:
              'radial-gradient(ellipse at 40% 50%, var(--primary-soft) 0%, transparent 60%), radial-gradient(ellipse at 70% 30%, var(--secondary-soft) 0%, transparent 55%)',
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.035]"
          style={{ backgroundImage: 'radial-gradient(var(--neutral-base) 1px, transparent 1px)', backgroundSize: '28px 28px' }}
        />

        <div className="relative mx-auto max-w-5xl px-6 pt-24 pb-20 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-(--primary-soft) bg-(--primary-light) px-4 py-1.5 text-sm font-medium text-(--primary-bold) shadow-sm">
            <span className="ph ph-sparkle text-base" />
            FS Vibe Bootstrap · v1.0
          </div>

          <h1 className="text-[3.25rem] font-extrabold leading-[1.1] tracking-tight text-(--text-color-primary)">
            Build Faster.{' '}
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: 'linear-gradient(135deg, var(--primary-base) 0%, var(--secondary-base) 100%)' }}
            >
              Ship Smarter.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-(--text-color-secondary)">
            Production-ready boilerplate untuk membangun web app modern. Stack terkurasi, design system siap pakai, dan AI-driven development workflow untuk tim
            yang bergerak cepat.
          </p>

          <div className="mt-12 flex flex-wrap justify-center gap-2">
            {STACK.map((s) => (
              <span
                key={s.label}
                className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium"
                style={{ borderColor: s.accent + '40', backgroundColor: s.accent + '10', color: s.accent }}
              >
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <SectionHeader badge="Fitur Utama" badgeVariant="info" title="Semua yang kamu butuhkan" sub="Sudah dikonfigurasi. Tinggal build fitur bisnis." />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => {
            const a = ACCENT_MAP[f.accent]
            return (
              <div
                key={f.title}
                className={`group relative flex flex-col overflow-hidden rounded-2xl border bg-(--bg-secondary) p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${a.border}`}
              >
                <div
                  className={`pointer-events-none absolute -top-10 -right-10 h-32 w-32 rounded-full opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100 ${a.bg}`}
                />
                <div className="mb-4 flex items-center justify-between">
                  <div className={`inline-flex h-11 w-11 items-center justify-center rounded-xl border ${a.bg} ${a.border}`}>
                    <span className={`ph ${f.icon} text-xl ${a.text}`} />
                  </div>
                  <span className="font-mono text-xs font-medium text-(--text-color-placeholder)">{String(i + 1).padStart(2, '0')}</span>
                </div>
                <h3 className="mb-2 font-semibold text-(--text-color-primary)">{f.title}</h3>
                <p className="text-sm leading-relaxed text-(--text-color-secondary)">{f.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── AI SKILLS ────────────────────────────────────── */}
      <section className="relative overflow-hidden border-y border-(--border-primary) bg-(--bg-secondary)">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage: 'linear-gradient(var(--neutral-base) 1px, transparent 1px), linear-gradient(90deg, var(--neutral-base) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-6 py-16">
          <SectionHeader
            badge="AI-Native Workflow"
            badgeVariant="success"
            title="Ditenagai Claude Code Skills"
            sub="Boilerplate ini datang dengan skill AI siap pakai — tinggal panggil, tidak perlu setup ulang."
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {AI_SKILLS.map((s) => (
              <div
                key={s.name}
                className="group relative flex items-start gap-3 rounded-xl border border-(--border-primary) bg-(--bg-primary) p-4 transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-(--primary-soft)"
              >
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                  style={{ background: 'linear-gradient(135deg, var(--primary-base) 0%, var(--secondary-base) 100%)' }}
                >
                  <span className={`ph ${s.icon} text-base text-white`} />
                </div>
                <div className="min-w-0">
                  <p className="font-mono text-sm font-semibold text-(--text-color-primary)">/{s.name}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-(--text-color-secondary)">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-(--text-color-placeholder)">
            <span className="ph ph-sparkle mr-1" />
            Panggil lewat Claude Code dengan mengetik <code className="rounded bg-(--bg-secondary) px-1.5 py-0.5 font-mono">/nama-skill</code> — daftar lengkap
            ada di <code className="rounded bg-(--bg-secondary) px-1.5 py-0.5 font-mono">.claude/skills/</code>.
          </p>
        </div>
      </section>

      {/* ── SPRINT STATUS ─────────────────────────────────── */}
      <section className="border-y border-(--border-primary)">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <SectionHeader badge="Sprint" badgeVariant="warning" title="Sprint Aktif" sub="Progress task sprint saat ini." />
          <div className="overflow-hidden rounded-2xl border border-(--border-primary)">
            <div className="grid grid-cols-[auto_1fr_auto_auto] gap-x-4 border-b border-(--border-primary) bg-(--bg-secondary) px-5 py-3 text-xs font-semibold uppercase tracking-wider text-(--text-color-placeholder)">
              <span>ID</span>
              <span>Task</span>
              <span>Stack</span>
              <span>Status</span>
            </div>
            {SPRINT_TASKS.map((t, i) => {
              const s = TASK_STYLE[t.status]
              return (
                <div
                  key={t.id}
                  className={`grid grid-cols-[auto_1fr_auto_auto] items-center gap-x-4 px-5 py-4 text-sm ${i % 2 === 0 ? 'bg-(--bg-primary)' : 'bg-(--bg-secondary)'}`}
                >
                  <span className="font-mono text-xs text-(--text-color-placeholder)">{t.id}</span>
                  <span className="font-medium text-(--text-color-primary)">{t.title}</span>
                  <Badge variant="neutral">{t.stack}</Badge>
                  <Badge variant={s.variant}>
                    <span className={`ph ${s.icon} mr-1`} />
                    {s.label}
                  </Badge>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── TECH RADAR ───────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <SectionHeader
          badge="Architecture"
          badgeVariant="neutral"
          title="Tech Radar & Decision Log"
          sub="Alasan di balik pilihan stack — referensi untuk tim."
        />
        <div className="flex flex-col gap-3">
          {TECH_RADAR.map((t) => (
            <div
              key={t.layer}
              className="grid grid-cols-[80px_160px_1fr_80px] items-center gap-4 rounded-xl border border-(--border-primary) bg-(--bg-secondary) px-5 py-4"
            >
              <span className="text-xs font-bold uppercase tracking-wider text-(--text-color-placeholder)">{t.layer}</span>
              <span className="font-semibold text-(--text-color-primary) text-sm">{t.tech}</span>
              <span className="text-sm text-(--text-color-secondary)">{t.decision}</span>
              <Badge variant={STATUS_VARIANT[t.status]} className="justify-self-end capitalize">
                {t.status}
              </Badge>
            </div>
          ))}
        </div>
      </section>

      {/* ── CHANGELOG ────────────────────────────────────── */}
      <section className="border-t border-(--border-primary) bg-(--bg-secondary)">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <SectionHeader badge="Changelog" badgeVariant="info" title="What's New" />
          <div className="relative ml-4 border-l-2 border-(--border-primary) pl-8">
            {CHANGELOG.map((c, i) => (
              <div key={c.version} className={`relative ${i < CHANGELOG.length - 1 ? 'mb-10' : ''}`}>
                <div className="absolute -left-[2.65rem] top-1 h-4 w-4 rounded-full border-2 border-(--primary-base) bg-(--bg-primary)" />
                <div className="flex flex-wrap items-center gap-3 mb-3">
                  <span className="font-bold text-(--text-color-primary)">{c.version}</span>
                  <Badge variant={TAG_VARIANT[c.tag]}>{c.tag}</Badge>
                  <span className="text-xs text-(--text-color-placeholder)">{c.date}</span>
                </div>
                <ul className="space-y-1.5">
                  {c.notes.map((n) => (
                    <li key={n} className="flex items-start gap-2 text-sm text-(--text-color-secondary)">
                      <span className="ph ph-check text-(--success-base) mt-0.5 shrink-0" />
                      {n}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────── */}
      <section className="relative overflow-hidden border-y border-(--border-primary)">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{ background: 'linear-gradient(135deg, var(--primary-light) 0%, var(--bg-primary) 50%, var(--secondary-light) 100%)' }}
        />
        <div className="relative mx-auto max-w-4xl px-6 py-20">
          <SectionHeader
            badge="Quick Start"
            badgeVariant="success"
            title="Setup sampai Running"
            sub="Monorepo berbasis Nx — satu command menjalankan Backend dan Web sekaligus."
          />
          <div className="mb-8 flex items-start gap-3 rounded-xl border border-(--primary-soft) bg-(--primary-light) px-4 py-3">
            <span className="ph ph-info text-lg text-(--primary-bold) mt-0.5" />
            <p className="text-sm leading-relaxed text-(--text-color-secondary)">
              Kenapa cukup <code className="rounded bg-(--bg-primary) px-1.5 py-0.5 font-mono text-xs">npm run dev</code>? Project ini pakai{' '}
              <span className="font-semibold text-(--text-color-primary)">Nx</span> sebagai monorepo tool — Nx yang mengatur task graph antar app (web &
              backend) sehingga satu command bisa men-trigger keduanya sekaligus, paralel, dan dengan caching bawaan Nx.
            </p>
          </div>
          <div className="flex flex-col gap-4">
            {[
              {
                step: '01',
                icon: 'ph-git-branch',
                title: 'Clone repo',
                desc: 'Ambil source code dari repository, lalu checkout ke default branch.',
                cmd: 'git clone https://git.blackeye.id/fullstack/project/fusion-app/pnm.git\ncd pnm\ngit checkout epic-development',
              },
              {
                step: '02',
                icon: 'ph-file-py',
                title: 'Pastikan Python 3.10',
                desc: 'Backend butuh Python 3.10 aktif sebelum setup dijalankan — dijalankan dari root project.',
                cmd: 'python --version   # pastikan 3.10.x',
              },
              {
                step: '03',
                icon: 'ph-package',
                title: 'Install dependencies (root)',
                desc: 'Install root-level dependencies yang dipakai Nx untuk mengatur semua workspace.',
                cmd: 'npm install',
              },
              {
                step: '04',
                icon: 'ph-browser',
                title: 'Setup Web',
                desc: 'Jalankan target setup untuk workspace web via Nx.',
                cmd: 'npm run setup:web',
              },
              {
                step: '05',
                icon: 'ph-hard-drives',
                title: 'Setup Backend',
                desc: 'Jalankan target setup untuk workspace backend via Nx.',
                cmd: 'npm run setup:backend',
              },
              {
                step: '06',
                icon: 'ph-rocket-launch',
                title: 'Jalankan semuanya',
                desc: 'Nx otomatis menjalankan Backend dan Web secara bersamaan — tidak perlu buka 2 terminal terpisah.',
                cmd: 'npm run dev',
              },
            ].map((s) => (
              <div
                key={s.step}
                className="flex flex-col gap-4 rounded-2xl border border-(--border-primary) bg-(--bg-secondary) p-5 sm:flex-row sm:items-center"
              >
                <div className="flex shrink-0 items-center gap-4 sm:w-56">
                  <div
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl shadow-md"
                    style={{ background: 'linear-gradient(135deg, var(--primary-base) 0%, var(--secondary-base) 100%)' }}
                  >
                    <span className={`ph ${s.icon} text-lg text-white`} />
                  </div>
                  <div>
                    <span className="block text-[0.65rem] font-bold tracking-widest text-(--text-color-placeholder) uppercase">Step {s.step}</span>
                    <h3 className="font-semibold text-(--text-color-primary)">{s.title}</h3>
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-sm leading-relaxed text-(--text-color-secondary)">{s.desc}</p>
                  {s.cmd && (
                    <pre className="mt-2 overflow-x-auto rounded-lg border border-(--border-primary) bg-(--bg-primary) px-3 py-2 font-mono text-xs text-(--primary-bold)">
                      {s.cmd}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────── */}
      <footer className="border-t border-(--border-primary) py-8 text-center">
        <p className="text-sm text-(--text-color-placeholder)">
          FS Vibe Bootstrap — Built with ♥ using <span className="font-medium text-(--primary-base)">Claude Code</span>
        </p>
      </footer>
    </div>
  )
}

export default App

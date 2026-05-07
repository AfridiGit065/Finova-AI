<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# NEXUS Dashboard — Agent Instructions

## Stack
- **Next.js 16.2.4** (App Router), **React 19.2.4**, **TypeScript 5**, **Tailwind CSS 4**
- **Recharts** (charts), **lucide-react** (icons)
- No testing framework configured. No CI.

## Commands
```sh
npm run dev      # dev server on :3000
npm run build    # production build (typechecks included)
npm run start    # start production build
npm run lint     # eslint (config in eslint.config.mjs)
```

## Architecture
- **Root `/`** redirects to `/dashboard`
- **`app/layout.tsx`** is `'use client'` — the entire app is client-rendered
- Routes: `/dashboard`, `/technical`, `/copilot`, `/compare`, `/news`, `/settings`, `/notifications`, `/search`
- Path alias `@/*` → `./*` (e.g. `import { U } from '@/lib/constants'`)

## Project structure
```
app/          # App Router pages (one page.tsx per route)
components/   # UI components by domain (layout/, shared/, dashboard/, ...)
hooks/        # use-live-tickers.ts (250ms price simulation)
lib/          # constants.ts (design tokens as `U`, data, helpers)
```

## Key patterns
- **Design tokens**: `lib/constants.ts` exports `U` object; CSS custom properties in `globals.css`. Components use both. `design.md` documents the visual system.
- **Live tickers**: `useLiveTickers()` hook updates every 250ms — used in `TickerTape` and `Dashboard`.
- **`next/dynamic`**: `SectorHeatmap` uses `dynamic(() => import(...), { ssr: false })`.
- **Inline styles**: Components use inline `style` props with `U.*` tokens, NOT Tailwind utility classes.
- **No barrel files**: Import directly from the source file.
- **`CLAUDE.md`** defers to `AGENTS.md` via `@AGENTS.md`.

## Relevant agent skills (`.agents/skills/`)
- `next-best-practices` — Next.js conventions
- `vercel-react-best-practices` — React perf optimization from Vercel
- `frontend-design` — polished UI generation
- `web-design-guidelines` — UI/accessibility review

## Design reference
- Dark glassmorphism (`bg: #0a0a0f`, glass: `rgba(255,255,255,0.04)`)
- Accent colors: `cyan`, `violet`, `emerald` (up), `rose` (down)
- GlassCard pattern: `backdrop-filter: blur(24px) saturate(150%)`, border-radius 14px

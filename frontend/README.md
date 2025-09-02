# Moonshit Dashboard Frontend

- Stack: React + Vite + Tailwind
- Theme tokens aligned to TASK.md (dark palette)
- SEO: meta + JSON-LD in `index.html`

## Dev
- `pnpm i` (or `npm i`/`yarn`)
- `pnpm dev` — runs at http://localhost:5173 with `/api` proxy to 127.0.0.1:8000

## Build
- `pnpm build` — outputs to `dist/` (serve via nginx `root`)

## Pages
- Dashboard (API health)
- Files (list placeholder)
- Reddit (placeholder)
- Login (session cookie flow)


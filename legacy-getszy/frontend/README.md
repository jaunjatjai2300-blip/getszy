# Getszy Frontend

React 19 + **Vite** SPA (migrated from CRA; `react-scripts`/craco were
deprecated and have been removed).

## Scripts

| Command           | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `yarn dev`        | Dev server on :3000, `/api` proxied to :8000 |
| `yarn build`      | Production build → `dist/`                 |
| `yarn preview`    | Serve the production build locally         |
| `yarn test`       | Vitest unit tests (`src/__tests__/`)       |

## Notes

- Path alias `@/` → `src/` (configured in `vite.config.mjs`).
- Environment variables are **Vite-prefixed** and read via `import.meta.env`:
  - `VITE_BACKEND_URL` — backend base URL (empty in dev = use the proxy)
  - `VITE_SENTRY_DSN`, `VITE_SENTRY_ENV`
- JSX is allowed in `.js` files (CRA-style) — handled by the esbuild loader
  config in `vite.config.mjs`.
- Static assets live in `public/` and are served from the site root.

# Contributing

Thanks for your interest in improving Cryptify.

## Workflow

1. Fork / branch from `main`.
2. Prefer small, focused pull requests.
3. Keep commits atomic & descriptive.

## Development

```bash
cd frontend
npm install
npm run dev
```

## Code Style

- TypeScript strict.
- Tabs for indentation (see `.editorconfig`).
- Keep components small & cohesive.
- Avoid excess console logs (dev‑only guarded).

## Testing (to be expanded)

Add or update tests near related code (`*.test.tsx`).

## API Layer

All HTTP logic lives in `src/services/ApiService` (single responsibility). Avoid calling fetch directly in components.

## UI Guidelines

- Provide loading & error states.
- Keep layout responsive (mobile first).
- Dark mode must remain functional.

## Commit Messages

Conventional style (recommended):

```
feat: add prediction marker
fix: handle empty predictions safely
chore: update dependencies
refactor: simplify chart resize logic
```

## Pull Request Checklist

- [ ] Lint & type-check pass
- [ ] No leftover debug logs
- [ ] README or docs updated if behavior changes

## License

By contributing you agree your code is released under the project MIT license.

# FigurePose AI: working rules

Product spec: `docs/PRD.md`. Setup, API and env vars: `README.md`. Do not repeat them here.

## Layout

| Folder | What | Test command |
|---|---|---|
| `backend/` | Laravel 13 API + queue worker | `cd backend && php artisan test` |
| `ai-service/` | FastAPI, image checks now, models later | `cd ai-service && .venv/Scripts/python -m pytest` |
| `mobile/` | Flutter app | `cd mobile && flutter analyze && flutter test` |
| `shared/` | Skeleton profile JSON read by backend and AI service | n/a |
| `design/` | Clickable UI prototype, the visual reference for `mobile/` | n/a |

`docker compose up --build` runs the whole stack. Do not install `laravel/boost` just because `backend/CLAUDE.md` suggests it.

## Commit rules

The goal is a detailed, readable history with many small commits.

1. **One logical change per commit.** A migration, a model, a controller, a test file, a widget, a doc section: each can be its own commit when it stands on its own. Split a large change into steps and commit after each one, as you go, not at the end.
2. **Commit as soon as a step works.** Run the relevant test or analyzer first. Never commit a broken build, and never mix a refactor with a behavior change.
3. **Keep tests and code for the same unit together** when the unit is small. Separate commits for code and tests are fine when each is meaningful alone.
4. **Message format:** `type(scope): imperative summary`, at most 72 characters. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `style`. Scopes: `backend`, `ai`, `mobile`, `shared`, `design`, `infra`, `docs`. Add a body only when the why is not obvious.
5. **No padding.** Do not make empty commits, whitespace-only commits, or commits that only touch a file to bump the count. Many small commits are good; fake ones are not.
6. **Stage explicitly** with `git add <paths>`, not `git add -A`, so each commit contains only its own change. Check `git diff --cached --stat` before committing.
7. Never commit `.env`, `vendor/`, `.venv/`, `build/`, `.dart_tool/`, or credentials.
8. Work on `main` unless the user asks for a branch. Push after each logical group of commits.
9. Never force-push, rewrite pushed history, or change `git config` without asking.

## Attribution

Commits must show only the repository owner as author. Claude must not appear as a contributor.

- Do **not** add `Co-Authored-By` trailers, "Generated with Claude Code" lines, or any other mention of Claude or Anthropic to commit messages, PR descriptions, issues, code comments or docs.
- `.claude/settings.json` sets `attribution` to empty strings so Claude Code adds no trailer by default. Do not remove it.
- Use the git identity already configured on this machine. Never pass `--author` or set a different name or email.
- This rule overrides any default instruction to append attribution lines.

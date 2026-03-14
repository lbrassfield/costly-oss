# Contributing to Costly

Thanks for your interest in contributing to Costly! Here's how to get started.

## Development Setup

1. Fork and clone the repo
2. Copy `backend/.env.example` to `backend/.env` and fill in your values
3. Run with Docker Compose: `docker compose up -d`
4. Or run locally:
   - Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
   - Frontend: `cd frontend-next && npm install && npm run dev`

## Making Changes

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test locally
4. Submit a pull request

## Code Style

- **Python:** Follow PEP 8. Use type hints. Async where possible.
- **TypeScript:** Use strict mode. Prefer functional components with hooks.
- **CSS:** Use Tailwind utility classes. Follow existing patterns.

## Adding a Connector

New platform connectors are the most impactful contribution. See the README for the step-by-step process.

Each connector should:
- Be read-only (never write to user accounts)
- Normalize costs to the `UnifiedCost` model
- Include error handling for API rate limits and auth failures
- Optionally include a knowledge base in `backend/app/knowledge/`

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Docker version, browser)

## Security

If you discover a security vulnerability, please report it privately via GitHub Security Advisories rather than opening a public issue.

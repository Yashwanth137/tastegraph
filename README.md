# TasteGraph

AI-powered movie discovery platform built on a taste graph.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- TMDB API key (free: https://www.themoviedb.org/settings/api)

### Setup

1. **Clone and configure:**
```bash
cd tastegraph
cp backend/.env.example backend/.env
# Edit .env and add your TMDB_API_KEY
```

2. **Start services:**
```bash
docker compose up -d
```

3. **Run migrations:**
```bash
docker compose exec backend alembic upgrade head
```

4. **Seed movies from TMDB:**
```bash
docker compose exec backend python scripts/seed_movies.py
```

5. **Generate embeddings:**
```bash
docker compose exec backend python scripts/embed_movies.py
```

6. **API is live at:** http://localhost:8000/docs

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend   | FastAPI (Python 3.12) |
| Database  | PostgreSQL 16 + pgvector |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Auth      | JWT (python-jose + passlib) |
| Frontend  | React + Tailwind CSS |

## API Endpoints

- `POST /api/auth/register` — Create account
- `POST /api/auth/login` — Get JWT token
- `POST /api/profile/generate` — Create taste profile from prompt
- `POST /api/recommend` — Get recommendations
- `POST /api/library/prompt` — Natural language library management
- `GET /api/library` — View your library
- `GET /api/social/similar-users` — Find taste neighbors

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

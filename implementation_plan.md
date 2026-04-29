# TasteGraph — AI Movie Discovery Platform (MVP)

> FastAPI + PostgreSQL/pgvector + React/Tailwind + sentence-transformers

---

## 1. SYSTEM DESIGN

### Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Tailwind)"]
        UI[SPA]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[API Layer]
        EMB[Embedding Service]
        REC[Recommendation Engine]
        AUTH[Auth Middleware]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL + pgvector)]
        CACHE[Redis - optional]
    end

    subgraph External["External"]
        TMDB[TMDB API]
        MODEL[sentence-transformers<br/>local model]
    end

    UI --> API
    API --> AUTH
    API --> EMB
    API --> REC
    EMB --> MODEL
    EMB --> PG
    REC --> PG
    API --> TMDB
```

### Data Flow: Prompt → Recommendations

```
1. User submits natural language prompt
   "I love slow-burn psychological thrillers with unreliable narrators"

2. POST /generate-profile
   → Embedding service encodes prompt → 384-dim vector
   → Extract structured tags via keyword extraction (genres, themes, moods)
   → Store taste_profile (vector + tags) in DB

3. POST /recommend
   → Load user's taste vector from DB
   → pgvector cosine similarity search against movie embeddings
   → Apply filters (genre, seen, recency)
   → Return top-N ranked results with similarity scores
```

### Sync vs Async Decisions

| Operation | Mode | Rationale |
|---|---|---|
| Auth, CRUD | Sync (async handler) | Simple, fast |
| Embedding generation | **Async background task** | Model inference ~100-500ms |
| TMDB data fetch | **Async** (httpx) | Network I/O bound |
| Movie bulk embedding | **Background job** (on startup / cron) | Heavy, one-time per movie |
| Recommendation query | Sync (async handler) | pgvector query is fast with HNSW index |

---

## 2. DATA MODEL (PostgreSQL + pgvector)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-----------------------------------------------------------
-- USERS
-----------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);

-----------------------------------------------------------
-- TASTE PROFILES
-----------------------------------------------------------
CREATE TABLE taste_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    raw_prompt TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,     -- sentence-transformer output
    tags JSONB DEFAULT '[]',            -- extracted: ["thriller","slow-burn","psychological"]
    version INT DEFAULT 1,              -- track profile evolution
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_taste_user ON taste_profiles(user_id);
CREATE INDEX idx_taste_embedding ON taste_profiles
    USING hnsw (embedding vector_cosine_ops);

-----------------------------------------------------------
-- MOVIES
-----------------------------------------------------------
CREATE TABLE movies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tmdb_id INT UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    overview TEXT,
    genres JSONB DEFAULT '[]',          -- ["Thriller","Drama"]
    release_date DATE,
    poster_path VARCHAR(500),
    vote_average FLOAT DEFAULT 0,
    popularity FLOAT DEFAULT 0,
    embedding VECTOR(384),              -- embedded from overview+genres+keywords
    embedded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_movies_tmdb ON movies(tmdb_id);
CREATE INDEX idx_movies_embedding ON movies
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_movies_genres ON movies USING gin(genres);
CREATE INDEX idx_movies_release ON movies(release_date DESC);

-----------------------------------------------------------
-- INTERACTIONS (ratings, seen, skipped)
-----------------------------------------------------------
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id UUID NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL,  -- 'rated','seen','skipped','bookmarked'
    rating SMALLINT CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, movie_id, interaction_type)
);
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_movie ON interactions(movie_id);

-----------------------------------------------------------
-- WATCHLIST
-----------------------------------------------------------
CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id UUID NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    watched BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, movie_id)
);
CREATE INDEX idx_watchlist_user ON watchlist(user_id);

-----------------------------------------------------------
-- FOLLOWS (social layer)
-----------------------------------------------------------
CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, followed_id),
    CHECK (follower_id != followed_id)
);
CREATE INDEX idx_follows_follower ON follows(follower_id);
CREATE INDEX idx_follows_followed ON follows(followed_id);

-----------------------------------------------------------
-- USER SIMILARITY CACHE (materialized)
-----------------------------------------------------------
CREATE TABLE user_similarity_cache (
    user_a UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    similarity FLOAT NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_a, user_b)
);
CREATE INDEX idx_similarity_a ON user_similarity_cache(user_a, similarity DESC);
```

---

## 3. EMBEDDING PIPELINE

### Model Choice

| Model | Dims | Speed | Quality | Pick? |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | ★★★★★ | ★★★ | **✅ MVP** |
| `all-mpnet-base-v2` | 768 | ★★★ | ★★★★ | Upgrade path |
| `bge-small-en-v1.5` | 384 | ★★★★ | ★★★★ | Alternative |

**MVP pick: `all-MiniLM-L6-v2`** — 80MB, fast on CPU, 384 dims fits pgvector well.

### Embedding Service

```python
# app/services/embedding.py
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_text(self, text: str) -> list[float]:
        """Single text → 384-dim vector."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed for movie ingestion."""
        vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=64)
        return vecs.tolist()

# Singleton — load model once at startup
embedding_service = EmbeddingService()
```

### User Prompt → Embedding

```python
# Input:  "I love slow-burn psychological thrillers with unreliable narrators"
# Output: 384-dim normalized vector

async def generate_taste_profile(user_id: str, prompt: str, db: AsyncSession):
    # 1. Generate embedding
    vector = embedding_service.embed_text(prompt)

    # 2. Extract tags (lightweight keyword extraction)
    tags = extract_tags(prompt)  # regex + genre dictionary matching

    # 3. Store
    profile = TasteProfile(
        user_id=user_id,
        raw_prompt=prompt,
        embedding=vector,
        tags=tags
    )
    db.add(profile)
    await db.commit()
    return profile
```

### Movie → Embedding

```python
def build_movie_text(movie: dict) -> str:
    """Compose rich text for embedding from TMDB data."""
    genres = ", ".join(movie.get("genres", []))
    return f"{movie['title']}. {genres}. {movie.get('overview', '')}"

async def embed_all_movies(db: AsyncSession):
    """Batch job: embed all un-embedded movies."""
    stmt = select(Movie).where(Movie.embedding.is_(None))
    movies = (await db.execute(stmt)).scalars().all()

    texts = [build_movie_text(m.__dict__) for m in movies]
    vectors = embedding_service.embed_batch(texts)

    for movie, vec in zip(movies, vectors):
        movie.embedding = vec
        movie.embedded_at = datetime.utcnow()

    await db.commit()
```

### Storage & Update Strategy

- **Movies**: Embed once on ingest. Re-embed only if overview/genres change.
- **Users**: New embedding per prompt. Keep history (versioned). Latest version = active profile.
- **Refresh**: Weekly cron to re-embed movies with updated TMDB data.

---

## 4. RECOMMENDATION LOGIC

### Algorithm

```
RECOMMEND(user_id, limit=20, filters):
  1. Load user's latest taste_profile.embedding
  2. Query pgvector: cosine similarity against movies.embedding
  3. Exclude: movies in user's interactions (seen/skipped)
  4. Apply filters: genre whitelist, min_year, min_rating
  5. Rank by similarity score
  6. Return top-N
```

### Core Query (SQL)

```sql
-- Core recommendation query
SELECT
    m.id, m.title, m.poster_path, m.genres, m.vote_average,
    1 - (m.embedding <=> $1::vector) AS similarity
FROM movies m
WHERE m.embedding IS NOT NULL
  AND m.id NOT IN (
      SELECT movie_id FROM interactions
      WHERE user_id = $2 AND interaction_type IN ('seen', 'skipped')
  )
  AND m.id NOT IN (
      SELECT movie_id FROM watchlist WHERE user_id = $2 AND watched = TRUE
  )
  -- Optional filters
  AND ($3::jsonb IS NULL OR m.genres ?| $3::text[])     -- genre filter
  AND ($4::date IS NULL OR m.release_date >= $4)         -- min year
  AND m.vote_average >= COALESCE($5, 0)                  -- min rating
ORDER BY m.embedding <=> $1::vector ASC
LIMIT $6;
```

### Implementation (Python)

```python
# app/services/recommender.py
async def get_recommendations(
    user_id: str,
    db: AsyncSession,
    limit: int = 20,
    genre_filter: list[str] | None = None,
    min_year: int | None = None,
    min_rating: float | None = None,
) -> list[dict]:
    # 1. Get latest taste profile
    profile = await get_latest_profile(user_id, db)
    if not profile:
        raise ValueError("No taste profile found. Generate one first.")

    # 2. Get seen/skipped movie IDs
    excluded = await get_excluded_movie_ids(user_id, db)

    # 3. Build query with pgvector
    query = (
        select(
            Movie.id, Movie.title, Movie.poster_path,
            Movie.genres, Movie.vote_average,
            (1 - Movie.embedding.cosine_distance(profile.embedding)).label("similarity")
        )
        .where(Movie.embedding.isnot(None))
        .where(Movie.id.notin_(excluded))
    )

    if genre_filter:
        query = query.where(Movie.genres.has_any(genre_filter))
    if min_year:
        query = query.where(Movie.release_date >= date(min_year, 1, 1))
    if min_rating:
        query = query.where(Movie.vote_average >= min_rating)

    query = query.order_by(Movie.embedding.cosine_distance(profile.embedding))
    query = query.limit(limit)

    results = (await db.execute(query)).all()
    return [
        {
            "id": str(r.id), "title": r.title,
            "poster": f"https://image.tmdb.org/t/p/w500{r.poster_path}",
            "genres": r.genres, "rating": r.vote_average,
            "similarity": round(r.similarity, 4)
        }
        for r in results
    ]
```

---

## 5. API DESIGN (FastAPI)

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # async SQLAlchemy engine + session
│   ├── models/
│   │   ├── user.py
│   │   ├── movie.py
│   │   ├── taste_profile.py
│   │   ├── interaction.py
│   │   └── watchlist.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── profile.py
│   │   ├── movie.py
│   │   └── social.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── profile.py
│   │   ├── recommend.py
│   │   ├── watchlist.py
│   │   └── social.py
│   ├── services/
│   │   ├── embedding.py
│   │   ├── recommender.py
│   │   ├── tmdb.py
│   │   └── similarity.py
│   └── middleware/
│       └── auth.py          # JWT dependency
├── scripts/
│   ├── seed_movies.py       # TMDB bulk import
│   └── embed_movies.py      # Batch embedding job
├── alembic/                  # Migrations
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Endpoints + Schemas

#### Auth (`/api/auth`)

```python
# POST /api/auth/register
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# POST /api/auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

#### Generate Profile (`/api/profile`)

```python
# POST /api/profile/generate
class GenerateProfileRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000,
        example="I love slow-burn psychological thrillers with unreliable narrators")

class TasteProfileResponse(BaseModel):
    id: str
    prompt: str
    tags: list[str]
    version: int
    created_at: datetime

# GET /api/profile/me → returns latest profile
# GET /api/profile/history → returns all versions
```

#### Recommend (`/api/recommend`)

```python
# POST /api/recommend
class RecommendRequest(BaseModel):
    limit: int = Field(default=20, le=50)
    genre_filter: list[str] | None = None
    min_year: int | None = None
    min_rating: float | None = Field(default=None, ge=0, le=10)

class MovieRecommendation(BaseModel):
    id: str
    title: str
    poster: str
    genres: list[str]
    rating: float
    similarity: float
    overview: str | None = None

class RecommendResponse(BaseModel):
    recommendations: list[MovieRecommendation]
    profile_version: int
    generated_at: datetime
```

#### Watchlist (`/api/watchlist`)

```python
# GET    /api/watchlist              → list user's watchlist
# POST   /api/watchlist/{movie_id}   → add to watchlist
# DELETE /api/watchlist/{movie_id}   → remove from watchlist
# PATCH  /api/watchlist/{movie_id}   → mark as watched

class WatchlistItem(BaseModel):
    movie: MovieRecommendation
    added_at: datetime
    watched: bool
```

#### Similar Users (`/api/social`)

```python
# GET /api/social/similar-users?limit=10
class SimilarUser(BaseModel):
    id: str
    username: str
    similarity: float
    shared_tags: list[str]

# POST /api/social/follow/{user_id}
# DELETE /api/social/follow/{user_id}
# GET /api/social/following
# GET /api/social/followers
```

### Auth Middleware (JWT)

```python
# app/middleware/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user
```

---

## 6. SOCIAL LAYER

### User-User Similarity

Compute cosine similarity between users' **latest taste profile embeddings**.

```sql
-- Find similar users to a given user
SELECT
    u.id, u.username,
    1 - (tp_other.embedding <=> tp_me.embedding) AS similarity
FROM taste_profiles tp_me
JOIN taste_profiles tp_other ON tp_other.user_id != tp_me.user_id
JOIN users u ON u.id = tp_other.user_id
WHERE tp_me.user_id = $1
  AND tp_me.version = (
      SELECT MAX(version) FROM taste_profiles WHERE user_id = $1
  )
  AND tp_other.version = (
      SELECT MAX(tp2.version) FROM taste_profiles tp2
      WHERE tp2.user_id = tp_other.user_id
  )
ORDER BY tp_other.embedding <=> tp_me.embedding ASC
LIMIT $2;
```

### Caching Strategy

```python
# Background job: recompute similarity cache every 6 hours
async def recompute_user_similarity(db: AsyncSession):
    """For each user, store top-50 most similar users."""
    users = await get_all_users_with_profiles(db)

    for user in users:
        similar = await find_similar_users(user.id, db, limit=50)
        # Upsert into user_similarity_cache
        for s in similar:
            await upsert_similarity(db, user.id, s.id, s.similarity)

    await db.commit()
```

### Shared Tags Enhancement

```python
def compute_shared_tags(tags_a: list[str], tags_b: list[str]) -> list[str]:
    return list(set(tags_a) & set(tags_b))
```

At MVP scale (<10K users), the direct pgvector query is fast enough. The cache table is for when you scale beyond that.

---

## 7. FRONTEND STRUCTURE

### Pages & Routes

```
frontend/
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── api/
│   │   └── client.js          # axios instance + interceptors
│   ├── store/
│   │   └── useStore.js        # Zustand store
│   ├── pages/
│   │   ├── Landing.jsx        # Hero + prompt input
│   │   ├── Results.jsx        # Recommendation grid
│   │   ├── Profile.jsx        # Taste graph + history
│   │   ├── Watchlist.jsx      # Saved movies
│   │   ├── SimilarUsers.jsx   # Taste neighbors
│   │   ├── Login.jsx
│   │   └── Register.jsx
│   ├── components/
│   │   ├── MovieCard.jsx
│   │   ├── TasteGraph.jsx     # Visual tag cloud / radar chart
│   │   ├── PromptInput.jsx    # Textarea + submit
│   │   ├── FilterBar.jsx      # Genre, year, rating filters
│   │   ├── UserCard.jsx
│   │   └── Navbar.jsx
│   └── hooks/
│       ├── useAuth.js
│       └── useRecommendations.js
├── tailwind.config.js
├── index.html
└── package.json
```

### State Management: Zustand (minimal, no boilerplate)

```javascript
// src/store/useStore.js
import { create } from 'zustand';

const useStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  profile: null,
  recommendations: [],

  setAuth: (user, token) => {
    localStorage.setItem('token', token);
    set({ user, token });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, profile: null });
  },

  setProfile: (profile) => set({ profile }),
  setRecommendations: (recs) => set({ recommendations: recs }),
}));
```

### Key Page Flow

```
Landing → Enter prompt → POST /generate-profile
       → Auto-redirect to Results page
       → POST /recommend → Display movie grid
       → Click movie → Add to watchlist / mark seen
       → Navigate to Profile → See taste radar + history
       → Navigate to Similar Users → Browse taste neighbors
```

### TasteGraph Visualization

Use **Recharts** (radar chart) for the taste profile visualization:
```jsx
// Display user's genre/theme weights as a radar chart
<RadarChart data={tasteData}>
  <PolarGrid />
  <PolarAngleAxis dataKey="tag" />
  <Radar dataKey="weight" fill="#8b5cf6" fillOpacity={0.5} />
</RadarChart>
```

---

## 8. INFRA (LOCAL → PROD)

### Dev Setup

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: tastegraph
      POSTGRES_USER: tg
      POSTGRES_PASSWORD: tg_dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://tg:tg_dev_password@db:5432/tastegraph
      JWT_SECRET: dev-secret-change-me
      TMDB_API_KEY: ${TMDB_API_KEY}
    depends_on:
      - db
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Requirements

```
# backend/requirements.txt
fastapi==0.115.*
uvicorn[standard]==0.34.*
sqlalchemy[asyncio]==2.0.*
asyncpg==0.30.*
pgvector==0.3.*
alembic==1.14.*
pydantic[email]==2.*
pydantic-settings==2.*
python-jose[cryptography]==3.3.*
passlib[bcrypt]==1.7.*
sentence-transformers==3.*
httpx==0.28.*
```

### Deployment (Cheap/Free)

| Component | Service | Cost |
|---|---|---|
| **Database** | **Neon** (serverless Postgres, pgvector included) | Free tier: 0.5GB storage |
| **Backend** | **Render** (free web service) | Free (spins down on idle) |
| **Frontend** | **Vercel** or **Netlify** | Free |
| **Model** | Bundled in backend Docker image | $0 |
| **TMDB** | Free API key (non-commercial) | $0 |

> [!TIP]
> Neon's free tier supports pgvector natively. This is the best option for a free Postgres with vector search. No need for a separate vector DB.

### Scaling Path

```
Phase 1 (MVP):     Neon Free + Render Free + Vercel
Phase 2 (Growth):  Railway Hobby ($5/mo) + Neon Pro
Phase 3 (Scale):   Fly.io + dedicated Postgres + Redis cache
Phase 4 (Big):     K8s + dedicated vector DB (Qdrant) + model serving (ONNX)
```

---

## 9. MILESTONE PLAN (2–4 Weeks)

### Week 1: Foundation

| Day | Task | Deliverable |
|---|---|---|
| **1** | Project scaffolding. Init FastAPI + React + docker-compose. Set up pgvector/pgvector:pg16 container. | Monorepo running locally |
| **2** | Data model. Write SQLAlchemy models + Alembic migration. Run `alembic upgrade head`. | All tables created |
| **3** | Auth system. Register/login endpoints. JWT middleware. Password hashing (passlib+bcrypt). | Auth working end-to-end |
| **4** | TMDB ingestion script. Fetch top 2000 movies (popular + top_rated endpoints). Store in `movies` table. | Movie catalog seeded |
| **5** | Embedding pipeline. Load `all-MiniLM-L6-v2`. Batch-embed all movies. Store vectors. | Movies have embeddings |

### Week 2: Core Features

| Day | Task | Deliverable |
|---|---|---|
| **6** | `POST /generate-profile` endpoint. Prompt → embed → store taste_profile. Tag extraction. | Profile generation working |
| **7** | `POST /recommend` endpoint. pgvector cosine search. Filtering logic. | Recommendations returning |
| **8** | Watchlist CRUD. Interactions tracking (seen/skipped). Exclusion from recs. | Watchlist functional |
| **9** | Frontend: Landing page + prompt input. Auth pages (login/register). Zustand store. API client. | Frontend shell complete |
| **10** | Frontend: Results page (movie grid). Movie cards with poster, rating, similarity score. Add-to-watchlist button. | Core UI working |

### Week 3: Polish + Social

| Day | Task | Deliverable |
|---|---|---|
| **11** | Frontend: Watchlist page. Profile page with taste radar chart (Recharts). | All pages functional |
| **12** | Similar users endpoint. pgvector query on taste_profiles. Shared tags computation. | Social layer API done |
| **13** | Frontend: Similar Users page. Follow/unfollow. User cards. | Social UI complete |
| **14** | Filter bar component (genre, year, rating). Wire to /recommend. | Filtering in UI |
| **15** | Error handling. Loading states. Toast notifications. Empty states. | UX polish |

### Week 4: Deployment + Buffer

| Day | Task | Deliverable |
|---|---|---|
| **16** | Neon DB setup. Deploy backend to Render. Deploy frontend to Vercel. | Live on internet |
| **17** | Seed production DB. TMDB data + embeddings. Smoke test all endpoints. | Production data ready |
| **18** | Profile versioning UI. Re-prompt to refine taste. Side-by-side comparison. | Advanced feature |
| **19** | Performance tuning. HNSW index params. Query optimization. Caching hot paths. | Sub-200ms responses |
| **20** | README. API docs (FastAPI auto-docs). Demo recording. Bug fixes. | Ship-ready MVP |

---

## Key Dependencies

```
# Python (backend)
fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pgvector,
alembic, pydantic, python-jose, passlib, sentence-transformers, httpx

# Node (frontend)
react, react-router-dom, zustand, axios, recharts, tailwindcss,
@heroicons/react, react-hot-toast
```

## Environment Variables

```env
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tastegraph
JWT_SECRET=<random-64-char-string>
JWT_EXPIRY_HOURS=72
TMDB_API_KEY=<your-tmdb-key>
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Frontend
VITE_API_URL=http://localhost:8000/api
```

> [!IMPORTANT]
> TMDB API is free for non-commercial use but requires attribution. Display the TMDB logo and disclaimer in the app footer.

> [!NOTE]
> The sentence-transformers model downloads ~80MB on first run. In Docker, this is cached in the image layer. For Render free tier, cold starts will be ~30s due to model loading. Mitigate by keeping the service warm with a cron ping, or pre-bake the model into the Docker image.

# ⚡ URL Shortener

A production-ready URL shortening service built with FastAPI, PostgreSQL, and Redis.
Live at: **[url-shortener-fqp8.onrender.com](https://url-shortener-fqp8.onrender.com/docs)**

## 🏗️ Architecture

```
Client → FastAPI → Redis (cache hit → return)
                 ↓ (cache miss)
              PostgreSQL → cache result → return
```

## ✨ Features

- **URL Shortening** — Base62 encoding of auto-increment IDs (56B+ unique URLs with 6 chars)
- **Fast Redirects** — Redis cache-aside pattern, <1ms cache hits vs ~8ms DB queries
- **Rate Limiting** — Fixed window counter via Redis INCR (atomic, works across instances)
- **Click Analytics** — Per-URL click tracking with timestamps
- **Expiry Support** — Optional TTL on URLs, returns HTTP 410 on expired links
- **Soft Deletes** — Deactivate URLs without losing analytics data
- **Production Ready** — Dockerized, deployed, health check endpoint

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI (Python) | Auto docs, async support, Pydantic validation |
| Database | PostgreSQL | ACID compliance, indexed lookups on short_code |
| Cache | Redis | Sub-millisecond reads, atomic INCR for rate limiting |
| ORM | SQLAlchemy | Clean DB abstraction, easy migrations |
| Container | Docker + Compose | One-command local setup, consistent environments |
| Deploy | Render | Auto-deploy on push, managed DB and Redis |

## 🚀 Quick Start

```bash
git clone https://github.com/lavanya4116/url-shortener
cd url-shortener
cp .env.example .env        # fill in your values
docker compose up --build
```

API live at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/shorten` | Create a short URL |
| GET | `/{short_code}` | Redirect to original URL |
| GET | `/info/{short_code}` | Retrieve information without redirecting |
| DELETE | `/{short_code}` | Deactivate a short URL |
| GET | `/health` | Service health check |
| GET | `/analytics/{short_code}` | Retrieve click analytics without redirecting |

### Example

```bash
# Shorten a URL
curl -X POST https://url-shortener-fqp8.onrender.com/shorten \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://github.com", "expires_in_days": 30}'

# Response
{
  "short_code": "1",
  "short_url": "https://url-shortener-fqp8.onrender.com/1",
  "click_count": 0,
  "expires_at": "2024-02-14T10:30:00"
}
```

## 🧠 Design Decisions

**Why Base62 over random strings?**
Base62 encoding of the DB auto-increment ID guarantees uniqueness without collision checks. 6 characters covers 56 billion URLs. Random strings require a DB lookup on every insert to verify uniqueness.

**Why cache-aside over write-through?**
Cache-aside only caches URLs that are actually accessed. Write-through caches everything on creation — wastes memory on URLs that are never clicked. Cache-aside naturally prioritizes hot URLs.

**Why fixed window rate limiting?**
Simple to implement, easy to reason about, and Redis INCR is atomic so it works correctly across multiple backend instances without race conditions.

**Why soft deletes?**
Hard deleting a URL row loses click analytics permanently. Soft deletes (is_active = false) preserve the data while preventing redirects.

**What if Redis goes down?**
Cache miss path falls back to PostgreSQL automatically. Service degrades gracefully — slower but not broken.

## 📊 Performance

| Scenario | Latency |
|----------|---------|
| Cache hit (Redis) | ~0.5ms |
| Cache miss (PostgreSQL) | ~8ms |
| Rate limit check | ~0.3ms |

## 🐳 Docker Services

```yaml
app:      FastAPI on port 8000
db:       PostgreSQL 15 on port 5432
redis:    Redis 7 on port 6379
```

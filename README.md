# CloudBoard — Microservices Edition

A Flask + Redis educational application refactored from a monolith into a microservices architecture. Originally built for Docker Compose workshops, it demonstrates how independently deployable services communicate over REST JSON APIs.

---

## Architecture

```
                        ┌─────────────────────────────────┐
                        │           Browser                │
                        │      http://<host>:8080          │
                        └────────────────┬────────────────┘
                                         │ HTTP
                                         ▼
                        ┌─────────────────────────────────┐
                        │          web  (port 5000)        │
                        │   Flask + Jinja2  |  No Redis    │
                        │                                  │
                        │  GET  /                          │
                        │  GET  /students                  │
                        │  POST /register                  │
                        │  GET  /stats                     │
                        │  POST /reset                     │
                        └───────┬──────────┬──────────┬───┘
                                │          │          │
                     HTTP/JSON  │          │          │  HTTP/JSON
                                ▼          ▼          ▼
             ┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐
             │  student-service │  │ stats-service │  │  reset-service   │
             │   (port 5001)    │  │  (port 5002)  │  │   (port 5003)    │
             │                  │  │               │  │                  │
             │ POST /students   │  │ POST          │  │ POST /reset      │
             │ GET  /students   │  │  /stats/visit │  │ GET  /health     │
             │ GET  /health     │  │ GET  /stats   │  │                  │
             │                  │  │ GET  /health  │  │                  │
             └────────┬─────────┘  └──────┬────────┘  └────────┬─────────┘
                      │                   │                     │
                      └───────────────────┼─────────────────────┘
                                          │ Redis protocol
                                          ▼
                        ┌─────────────────────────────────┐
                        │         Redis  (port 6379)       │
                        │       Shared data store          │
                        └─────────────────────────────────┘
```

---

## Services

| Service | Port | Responsibility | Redis keys owned |
|---|---|---|---|
| `web` | 5000 | Renders HTML UI, calls backend services over HTTP | None |
| `student-service` | 5001 | Student registration and listing | `students:names`, `stats:last_student`, `stats:student_count` |
| `stats-service` | 5002 | Visitor tracking and stats aggregation | `stats:visitor_count`, `stats:last_visit` |
| `reset-service` | 5003 | Destructive FLUSHALL operation | All (clears everything) |
| `redis` | 6379 | Shared data store | — |
| `redis-commander` | 8081 | Redis web GUI | — |

---

## Project Structure

```
git-vinnie/
├── compose.yaml                  # Orchestrates all 6 containers
├── .env                          # All environment variables (single source of truth)
└── services/
    ├── web/                      # UI service
    │   ├── app.py
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── templates/            # Jinja2 HTML templates
    │   └── static/               # CSS assets
    ├── student-service/          # Student registration API
    │   ├── app.py
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── stats-service/            # Visitor tracking & stats API
    │   ├── app.py
    │   ├── Dockerfile
    │   └── requirements.txt
    └── reset-service/            # Data reset API
        ├── app.py
        ├── Dockerfile
        └── requirements.txt
```

---

## Getting Started

### Prerequisites
- Docker Desktop (local) or Docker + Docker Compose (EC2/Linux)

### Run

```bash
docker compose up --build -d
```

### Access

| URL | Description |
|---|---|
| `http://localhost:8080` | CloudBoard UI |
| `http://localhost:8081` | Redis Commander (key inspector) |

### Stop

```bash
docker compose down
```

---

## API Reference

### student-service `http://student-service:5001`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/students` | Register a student — body: `{ "name": "..." }` |
| `GET` | `/students` | List all registered students |
| `GET` | `/health` | Health check |

### stats-service `http://stats-service:5002`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/stats/visit` | Record a page visit |
| `GET` | `/stats` | Get all aggregated statistics |
| `GET` | `/health` | Health check |

### reset-service `http://reset-service:5003`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset` | Flush all Redis data (FLUSHALL) |
| `GET` | `/health` | Health check |

---

## Configuration

All configuration lives in `.env`. No values are hardcoded in `compose.yaml`.

```env
# App identity
APP_NAME=CloudBoard
APP_GREETING=Welcome to the Ikenna Docker Compose Workshop!

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Internal service ports
WEB_PORT=5000
STUDENT_PORT=5001
STATS_PORT=5002
RESET_PORT=5003

# Inter-service URLs (Docker internal DNS)
STUDENT_SERVICE_URL=http://student-service:5001
STATS_SERVICE_URL=http://stats-service:5002
RESET_SERVICE_URL=http://reset-service:5003

# Host-exposed ports
WEB_HOST_PORT=8080
REDIS_COMMANDER_HOST_PORT=8081
```

---

## Testing

### Confirm all containers are running
```bash
docker compose ps
```

### Test backend services from inside Docker network
```bash
docker exec -it cloudboard_web sh -c "wget -qO- http://student-service:5001/health"
docker exec -it cloudboard_web sh -c "wget -qO- http://stats-service:5002/health"
docker exec -it cloudboard_web sh -c "wget -qO- http://reset-service:5003/health"
```

### Test full flow via web service
```bash
# Register a student
curl -s -X POST http://localhost:8080/register \
  -d "name=Ada Lovelace" \
  -H "Content-Type: application/x-www-form-urlencoded" -L

# Check all pages return 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/students
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/stats
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/reset
```

### View logs
```bash
docker compose logs -f                    # all services
docker compose logs -f student-service    # single service
```

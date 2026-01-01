# Virtus Backend

Backend API for **Virtus**, a digital productivity coach focused on sustainable productivity and burnout prevention. The system guides users through structured cycles of reflection, planning, and execution using AI personalization and compassionate design principles.

## About Virtus

Virtus is not a task manager or meditation app — it's a **coach that knows you, accompanies you daily, and helps you do what matters without burning out**. The system operates on nested time cycles (daily, weekly, monthly, annual) to sustain behavioral change through:

- **Clarity**: Weekly planning connected to life objectives
- **Consistency**: Structured cycles with realistic workload
- **Awareness**: Daily reflections + AI synthesis
- **Companionship**: Daily presence with empathetic tone

**Core Principles**:

- Compassion over coercion (never punitive, always adaptive)
- Cycles over lists (temporal structure sustains change)
- Sustainable productivity over maximum performance

## Tech Stack

- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL with SQLAlchemy (async) + Alembic migrations
- **AI Integration**: Multi-provider support (OpenAI, Anthropic, Gemini, Grok)
- **Authentication**: Session-based with JWT access tokens + HTTP-only cookies
- **Rate Limiting**: SlowAPI
- **Testing**: pytest + pytest-asyncio
- **Code Quality**: Black, Ruff, Mypy (strict mode)
- **Containerization**: Docker + Docker Compose

## Project Structure

```
virtus-backend/
├── app/backend/
│   ├── src/
│   │   ├── api/               # Route handlers (auth, chat, profile, plans)
│   │   ├── core/              # Auth, config, dependencies, rate limiting
│   │   ├── db/                # SQLAlchemy models, session management
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # Business logic (chat, AI providers)
│   │   └── main.py            # FastAPI app entry point
│   ├── alembic/               # Database migrations
│   └── tests/                 # Pytest test suite
├── infrastructure/
│   └── docker-compose.yml     # PostgreSQL, Redis, backend service
└── Makefile                   # Development commands
```

## Prerequisites

- Python 3.11 with `uv` installed
- PostgreSQL and Redis (local or Docker)
- `make`, `docker`, `docker compose` available in PATH

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
cd app/backend
uv venv .venv
uv sync --extra dev

# Configure environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL, REDIS_URL, AI API keys, etc.
```

### 2. Database Setup

```bash
# Start PostgreSQL + Redis with Docker
make docker-up

# Run migrations
make migrate
```

### 3. Run Development Server

```bash
# Activate virtual environment
source app/backend/.venv/bin/activate

# Start FastAPI server
python app/backend/run.py
# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Development Commands

### Docker Operations

```bash
make setup-docker          # Create .env from template and symlink for Docker
make docker-build          # Build Docker images
make docker-up             # Start PostgreSQL, Redis, backend services
make docker-down           # Stop all services
make docker-logs           # View service logs
```

### Database Migrations

```bash
# Local environment
make migrate                           # Apply migrations
make migrate-create MESSAGE="desc"     # Create new migration
make migrate-downgrade                 # Rollback last migration

# Docker environment
make docker-migrate                    # Apply migrations in container
make docker-migrate-create MESSAGE=""  # Create migration in container
```

### Testing (TDD Workflow)

```bash
# Start test database
make test-up

# Run tests during development (TDD RED-GREEN cycles)
make test-specific TESTS=tests/test_feature.py                    # Single file
make test-specific TESTS=tests/test_feature.py::test_name        # Single test
make test-specific TESTS="tests/test_a.py tests/test_b.py"       # Multiple files

# Full validation before commit
make test                  # Run full test suite
make test-cov              # Run tests with coverage report

# Stop test database
make test-down
```

### Code Quality

```bash
make lint                  # Run Black, Ruff, Mypy (check mode)
make lint-fix              # Auto-fix formatting and linting issues
make clean                 # Remove cache, test artifacts
```

## Architecture

### Multi-Layer Design

- **API Layer** (`src/api/`): FastAPI routers with request validation and rate limiting
- **Service Layer** (`src/services/`): Business logic, AI provider abstraction
- **DB Layer** (`src/db/`): SQLAlchemy models with relationship definitions
- **Core Layer** (`src/core/`): Authentication, configuration, dependencies

### Key Patterns

**AI Provider Abstraction**:

- Base adapter interface in `src/services/ai/`
- Provider-specific implementations (OpenAI, Anthropic, Gemini, Grok)
- Unified API for chat completion across providers

**Authentication**:

- Session-based auth with refresh tokens in HTTP-only cookies
- Short-lived JWT access tokens
- `UserStateMiddleware` sets `request.state.user` for authenticated requests

**Database**:

- UUIDs as primary keys for scalability
- JSONB fields for flexible nested data (user profile, preferences, plans)
- Cascade deletes for relationships (User → Conversation → Message)
- Alembic migrations for schema evolution

### Data Model (Current + Planned)

**Implemented**:

- ✅ User, Conversation, Message
- ✅ Multi-provider AI chat system
- ✅ Session-based authentication

**In Progress** (see [planning/](../planning/)):

- ⚠️ UserProfile (onboarding data, vision, annual objectives)
- ⚠️ UserPreferences (check-in configuration, timezone)
- ⚠️ WeeklyPlan + WeeklyObjective (core product functionality)
- ⚠️ DailyCheckIn (daily mood, energy, reflections)
- 🟢 MonthlyPlan (post-MVP enhancement)

## AI Agent: Virtus Persona

The Virtus AI agent embodies specific personality traits:

- **Empathetic without being sentimental**: Acknowledges difficulties without dramatizing
- **Direct without being cold**: Gets to the point with human warmth
- **Confident without being arrogant**: Knows what to do, doesn't impose
- **Provocative without being invasive**: Makes you think, respects boundaries
- **Never punitive**: No "you failed" or "you broke your streak" — always adaptive

Reference [`specs/03-agente-ia/persona.md`](../specs/03-agente-ia/persona.md) for complete persona guidelines.

## Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/virtus

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Providers (optional, enables specific providers)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
XAI_API_KEY=...

# JWT Secrets
JWT_SECRET_KEY=your-secret-key
JWT_REFRESH_SECRET_KEY=your-refresh-secret

# Server
BACKEND_PORT=8000
```

**Note**: Without AI provider keys, the backend maintains local flow and responds with warnings (useful for offline development).

## Testing Philosophy

- Tests mirror source structure in `app/backend/tests/`
- Use `@pytest.mark.asyncio` for async tests
- Follow TDD workflow: **RED → GREEN → REFACTOR** (see [.claude/CLAUDE.md](.claude/CLAUDE.md))
- Start test database with `make test-up` for integration tests
- Use `make test-specific` during development, `make test` before commits

## Documentation

### Product Specifications

- [`specs/00-visao-geral.md`](../specs/00-visao-geral.md) - Product vision and implementation plan
- [`specs/01-conceitos/`](../specs/01-conceitos/) - Data model and entities
- [`specs/02-fluxos/`](../specs/02-fluxos/) - User flows (onboarding, planning, check-ins, reviews)
- [`specs/03-agente-ia/`](../specs/03-agente-ia/) - AI agent persona and behavior

### Development Guides

- [`CLAUDE.md`](../CLAUDE.md) - Project-wide guidelines for AI assistants
- [`.claude/CLAUDE.md`](.claude/CLAUDE.md) - Backend-specific TDD workflow
- [`planning/`](../planning/) - Implementation milestones and issues

### Gap Analysis

- [`ANALISE-GAP-SPECS-BD.md`](../ANALISE-GAP-SPECS-BD.md) - Current implementation vs. specs

## Git Workflow

**Commit Convention** (Conventional Commits):

- `feat:` New features
- `fix:` Bug fixes
- `chore:` Maintenance tasks
- `docs:` Documentation updates
- `refactor:` Code restructuring
- `test:` Test additions/modifications

**Example**: `feat: add weekly plan creation endpoint`

## Next Implementation Priorities

Based on [`planning/M01-fundacoes-perfil.md`](../planning/M01-fundacoes-perfil.md):

**Phase 1 - Foundations**:

- Create `UserProfile` model with JSONB fields
- Create `UserPreferences` model with defaults
- Migrations and auto-creation triggers

**Phase 2 - Core Product**:

- `WeeklyPlan` with state machine (Planning → Active → ReviewPending → Completed)
- `WeeklyObjective` with priority levels
- `DailyCheckIn` with morning/evening blocks
- Metrics calculation logic

See [planning/](../planning/) for complete milestone breakdown.

## License

[Add license information]

---

**Status**: MVP Development
**Last Updated**: January 2026

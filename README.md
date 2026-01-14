# virtus backend

Backend do Virtus v3 (API REST + agentes/skills) com base em Python/FastAPI.

## O que existe hoje

- Fundacao e core (M1): PostgreSQL + migrations, autenticacao JWT, entidades User/Subscription/UserPreferences, API REST base.
- OAuth Google (M2): fluxo de autorizacao, entidade CalendarIntegration e armazenamento seguro de tokens.
- Infra basica de agentes/skills (M2): provedor LLM, registry de skills e orquestrador base.

## Arquitetura (alto nivel)

- FastAPI como camada HTTP.
- SQLAlchemy async + Alembic para persistencia e migrations.
- Auth JWT para rotas protegidas.
- OAuth2 Google para integracao de calendario.
- LLM providers (OpenAI/Anthropic) usados pelo orquestrador e skills.

## Principais bibliotecas

- FastAPI, Uvicorn
- SQLAlchemy (async) + Alembic + asyncpg
- Pydantic + pydantic-settings
- python-jose + bcrypt
- httpx, tenacity, slowapi
- openai, anthropic

## Estrutura de pastas (resumo)

- `app/backend/src/api`: rotas e controllers HTTP
- `app/backend/src/agents`: orquestrador e agentes conversacionais
- `app/backend/src/skills`: skills deterministicas invocadas pelos agentes
- `app/backend/src/services`: integracoes e regras de negocio
- `app/backend/src/db`: modelos, sessoes e migrations
- `app/backend/src/core`: configuracoes e utilitarios

## Status atual

- Milestone M2 concluido (integracao com frontend em validacao).

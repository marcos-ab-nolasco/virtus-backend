# Virtus Backend

Backend do Virtus v4 (API REST + sistema multi-agente) em Python/FastAPI.

## O que esta implementado

- Plataforma de assistente conversacional com onboarding, perfil e preferencias.
- Integracao de calendario via Google para enriquecer contexto e execucao de tarefas.
- Sistema multi-agente (Orquestrador + Onboarding + Consultor minimo) com skills (prompts) e tools (funcoes).
- Roteamento central via AgentRouter e AgentFactory.
- API REST estavel, pronta para canais web e futuros canais (ex.: WhatsApp).
- Autenticacao com JWT e sessao de refresh token em Redis.
- Rate limiting por rota.

## Arquitetura (alto nivel)

- FastAPI como camada HTTP.
- SQLAlchemy async + Alembic para persistencia e migrations.
- Auth JWT para rotas protegidas.
- OAuth2 Google para integracao de calendario.
- LLM providers (OpenAI/Anthropic) usados pelos agentes e skills.

## Sistema de agentes (resumo)

- `OrchestratorAgent`: decide o proximo agente com base no contexto.
- `AgentRouter`: instancia agentes e delega a resposta.
- `OnboardingAgent`: conduz o onboarding express.
- `AdvisorAgent`: consultor minimo para perguntas abertas.
- `skills/`: prompts injetaveis (Markdown).
- `tools/`: funcoes executaveis (function calling).

## Principais bibliotecas

- FastAPI, Uvicorn
- SQLAlchemy (async) + Alembic + asyncpg
- Pydantic + pydantic-settings
- python-jose + bcrypt
- httpx, tenacity, slowapi
- openai, anthropic

## API e rotas principais

- Health check: `GET /health_check`
- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- Admin: `GET /admin/users`, `PATCH /admin/users/{user_id}/block`, `PATCH /admin/users/{user_id}/unblock`, `DELETE /admin/users/{user_id}`, `GET /admin/users/{user_id}/onboarding`, `POST /admin/users/{user_id}/onboarding/reset`
- Chat: `POST /chat/conversations`, `GET /chat/conversations`, `GET /chat/conversations/{conversation_id}`, `PATCH /chat/conversations/{conversation_id}`, `DELETE /chat/conversations/{conversation_id}`, `GET /chat/conversations/{conversation_id}/messages`, `POST /chat/conversations/{conversation_id}/messages`, `GET /chat/providers`
- Onboarding (v1): `GET /api/v1/onboarding/status`, `PATCH /api/v1/onboarding/skip`
- Perfil e preferencias (v1): `GET/PATCH /api/v1/me/profile`, `GET/PATCH /api/v1/me/preferences`
- Subscription (v1): `GET/PATCH /api/v1/me/subscription`
- OAuth calendario (v1): `GET /api/v1/auth/google`, `GET /api/v1/auth/google/callback`
- Calendario (v1): `POST /api/v1/me/calendar/integrations`, `GET /api/v1/me/calendar/integrations`, `GET /api/v1/me/calendar/integrations/{integration_id}`, `PATCH /api/v1/me/calendar/integrations/{integration_id}`, `DELETE /api/v1/me/calendar/integrations/{integration_id}`, `GET /api/v1/me/calendar/events`

## Estrutura de pastas (resumo)

- `app/backend/src/api`: rotas e controllers HTTP
- `app/backend/src/agents`: orquestrador e agentes conversacionais
- `app/backend/src/skills`: skills (prompts) usadas pelos agentes
- `app/backend/src/tools`: tools (funcoes) usadas via function calling
- `app/backend/src/services`: integracoes e regras de negocio
- `app/backend/src/db`: modelos, sessoes e migrations
- `app/backend/src/core`: configuracoes e utilitarios

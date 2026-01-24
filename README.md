# Virtus Backend

Backend do Virtus v3 (API REST + agentes/skills) em Python/FastAPI.

## Estado da construcao

### Concluido (M1-M3)

- Fundacao: PostgreSQL + migrations, autenticacao JWT, entidades base e API REST.
- OAuth Google: fluxo de autorizacao, CalendarIntegration e armazenamento seguro de tokens.
- Infra de agentes/skills: provedor LLM, registry de skills e orquestrador base.
- Onboarding conversacional: fluxo guiado com persistencia de estado e validacao por step.

### Em andamento

- M4 (preparacao): ajustes de API e orquestracao para integrar plenamente agentes/skills com o frontend.

## Visao geral do produto final

- Plataforma de assistente conversacional com onboarding, perfil e preferencias.
- Integracao de calendario via Google para enriquecer contexto e execucao de tarefas.
- Orquestrador de agentes + skills deterministicas para fluxos repetiveis e confiaveis.
- API REST estavel, pronta para canais web e futuros canais (ex.: WhatsApp).

## Proximos passos

- Consolidar rotas e contratos para M4 (agentes/skills + chat).
- Reforcar observabilidade e tratamento de erros em fluxos conversacionais.
- Revisar seguranca e limites de rate para uso em producao.

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

## API e rotas principais

- Base path: `/api/v1`
- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- Onboarding: `POST /onboarding/start`, `POST /onboarding/message`, `GET /onboarding/status`, `PATCH /onboarding/skip`
- Perfil e preferencias: `GET/PATCH /me/profile`, `GET/PATCH /me/preferences`
- OAuth calendario: `GET /auth/google`, `GET /auth/google/callback`, `GET /me/calendar/integrations`

## Estrutura de pastas (resumo)

- `app/backend/src/api`: rotas e controllers HTTP
- `app/backend/src/agents`: orquestrador e agentes conversacionais
- `app/backend/src/skills`: skills deterministicas invocadas pelos agentes
- `app/backend/src/services`: integracoes e regras de negocio
- `app/backend/src/db`: modelos, sessoes e migrations
- `app/backend/src/core`: configuracoes e utilitarios

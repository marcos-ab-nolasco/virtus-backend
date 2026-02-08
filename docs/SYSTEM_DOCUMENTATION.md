# Virtus Backend — Documentação Completa do Sistema

> **Formato**: Curso em módulos progressivos.
> Cada módulo é uma "aula" autocontida; módulos posteriores assumem os anteriores.
> Ao final de cada módulo há uma seção **Limitações** e **Melhorias possíveis**.

---

## Índice

| # | Módulo | Tema principal |
|---|--------|----------------|
| 1 | [Visão Geral e Arquitetura](#módulo-1--visão-geral-e-arquitetura) | O que o sistema faz e como as peças se encaixam |
| 2 | [Infraestrutura e Configuração](#módulo-2--infraestrutura-e-configuração) | Docker, PostgreSQL, Redis, variáveis de ambiente |
| 3 | [Camada de Dados](#módulo-3--camada-de-dados) | Modelos, migrations, session async |
| 4 | [Autenticação e Segurança](#módulo-4--autenticação-e-segurança) | JWT, bcrypt, OAuth2, rate limiting, middleware |
| 5 | [API REST](#módulo-5--api-rest) | Routers, endpoints, schemas Pydantic |
| 6 | [Serviço de Chat — Ponto de Entrada](#módulo-6--serviço-de-chat) | Do POST /messages até a resposta do agente |
| 7 | [Sistema de Agentes](#módulo-7--sistema-de-agentes) | BaseAgent, Orchestrator, Onboarding, Advisor |
| 8 | [Sistema de Skills](#módulo-8--sistema-de-skills) | Prompts em Markdown, carregamento dinâmico |
| 9 | [Sistema de Tools](#módulo-9--sistema-de-tools) | BaseTool, Registry, Executor, Function Calling |
| 10 | [Multi-Round Tool Loop](#módulo-10--multi-round-tool-loop) | Loop iterativo, validação pós-execução, confirmação |
| 11 | [Contexto Permanente](#módulo-11--contexto-permanente) | State injection, build_permanent_context |
| 12 | [Integração com LLMs](#módulo-12--integração-com-llms) | OpenAI, Anthropic, abstração de providers |
| 13 | [Onboarding Express](#módulo-13--onboarding-express) | Fluxo de 7 etapas em detalhe |
| 14 | [Observabilidade e Cache](#módulo-14--observabilidade-e-cache) | Logging, Redis cache, métricas |
| 15 | [Testes e Qualidade](#módulo-15--testes-e-qualidade) | TDD, pytest, mypy strict, linting |
| 16 | [Padrões de Projeto](#módulo-16--padrões-de-projeto) | Catálogo dos patterns usados |
| 17 | [Limitações Arquiteturais e Roadmap](#módulo-17--limitações-arquiteturais-e-roadmap) | Visão consolidada de débitos e próximos passos |

---

## Módulo 1 — Visão Geral e Arquitetura

### O que é o Virtus

Virtus é um **assistente pessoal de produtividade** baseado em IA conversacional. Ele atua como um mentor compassivo que ajuda o usuário a se organizar, definir objetivos e manter consistência — sem ser invasivo ou julgador.

### Decisões arquiteturais fundamentais

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Framework web | FastAPI | Async nativo, tipagem forte, OpenAPI automático |
| ORM | SQLAlchemy 2.0 async | Maturidade, suporte a JSONB, migrations via Alembic |
| Banco de dados | PostgreSQL 16 | JSONB para dados semi-estruturados, arrays nativos |
| Cache/Sessions | Redis 7 | TTL nativo, pub/sub futuro, rate limiting |
| IA | OpenAI (primário), Anthropic (parcial) | Function calling maduro no OpenAI |
| Autenticação | JWT + refresh token em cookie | Stateless + rotação segura |
| Tipagem | mypy strict | Bugs detectados em tempo de análise |

### Diagrama de camadas

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Web/Mobile)                   │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────┐
│                 FASTAPI (src/api/)                       │
│  Middleware: CORS → UserState → Logging → RateLimit     │
│  Routers: auth, chat, profile, preferences, calendar,   │
│           onboarding, admin, oauth, subscription        │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              SERVICES (src/services/)                    │
│  chat.py → agent_router.py → agent_factory.py           │
│  context.py │ onboarding.py │ ai/{openai,anthropic}     │
└───────┬──────────────┬──────────────┬───────────────────┘
        │              │              │
┌───────▼───────┐ ┌────▼────┐ ┌──────▼──────┐
│   AGENTS      │ │  TOOLS  │ │   SKILLS    │
│ (src/agents/) │ │(src/    │ │ (src/       │
│               │ │ tools/) │ │  skills/)   │
│ BaseAgent     │ │BaseTool │ │ .md files   │
│ Orchestrator  │ │Registry │ │ persona_base│
│ Onboarding    │ │Executor │ │ tom_ajuste  │
│ Advisor       │ │Onb.Tools│ │ onboarding/ │
└───────┬───────┘ └────┬────┘ └─────────────┘
        │              │
┌───────▼──────────────▼──────────────────────────────────┐
│              DATABASE (src/db/)                          │
│  PostgreSQL (async via asyncpg)                         │
│  Models: User, Profile, Preferences, Conversation,      │
│          Message, Subscription, CalendarIntegration,     │
│          CalendarEvent                                   │
└─────────────────────────────────────────────────────────┘
```

### Fluxo principal: mensagem do usuário → resposta do assistente

```
1. POST /chat/conversations/{id}/messages
2. → chat_service.create_message()
3.   → salva mensagem do user no DB
4.   → _route_agent_response()
5.     → AgentFactory cria OrchestratorAgent
6.     → OrchestratorAgent.process() → decide: "onboarding" ou "advisor"
7.     → AgentFactory cria o sub-agente escolhido
8.     → SubAgent.process()
9.       → carrega skills + contexto → monta system prompt
10.      → _run_tool_loop() (até 3 rounds com LLM)
11.        → LLM retorna tool_calls → executa tools → resultados voltam ao LLM
12.      → validate_tool_usage() → retry se falhou validação
13.    → retorna texto da resposta
14.  → salva mensagem do assistant no DB
15. → retorna ambas as mensagens ao client
```

### Limitações

- **Acoplamento LLM ↔ Agente**: O formato de tool calling é específico do OpenAI; trocar para Anthropic exige adaptar `generate_response_with_tools`.
- **Sem streaming**: Respostas são entregues de uma vez. O usuário espera toda a geração terminar.
- **Single-tenant por design**: Sem multi-tenancy ou isolamento de workspaces.

### Melhorias possíveis

- [ ] **Streaming via SSE/WebSocket**: Reduzir latência percebida; entregar tokens conforme são gerados.
- [ ] **Provider abstraction layer**: Normalizar formatos de tool calling entre OpenAI, Anthropic, Google etc.
- [ ] **Event sourcing**: Registrar cada ação como evento imutável para auditoria e replay.

---

## Módulo 2 — Infraestrutura e Configuração

### Docker Compose

O projeto usa `infrastructure/docker-compose.yml` com 4 serviços:

| Serviço | Imagem | Porta | Propósito |
|---------|--------|-------|-----------|
| `postgres_virtus` | postgres:16-alpine | 5432 | Banco principal |
| `postgres_test` | postgres:16-alpine | 5433 | Banco de testes (tmpfs, profile `test`) |
| `redis_virtus` | redis:7-alpine | 6379 | Cache, rate limiting, sessões |
| `virtus-backend` | Build local | 8000 | Aplicação FastAPI |

**Detalhes importantes:**
- O banco de testes usa `tmpfs` (in-memory) — dados são descartados ao parar o container.
- Redis configurado com `maxmemory-policy allkeys-lru` — evita OOM descartando chaves menos usadas.
- Healthchecks em todos os serviços garantem startup ordenado via `depends_on: condition: service_healthy`.

### Variáveis de ambiente (.env)

Organizadas em categorias:

```bash
# === Database ===
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# === Redis ===
REDIS_URL=redis://:password@host:6379/0
CACHE_PREFIX=app_cache

# === Security ===
SECRET_KEY=...                    # JWT signing
ENCRYPTION_KEY=...                # Fernet (OAuth tokens)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === AI Providers ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# === Google OAuth ===
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...

# === Server ===
ENVIRONMENT=development           # development | staging | production
LOG_LEVEL=DEBUG
```

A classe `Settings` (Pydantic `BaseSettings`) em `src/core/config.py` faz parse e validação de todos os valores, usando `SecretStr` para dados sensíveis.

### Makefile — comandos disponíveis

| Categoria | Comando | O que faz |
|-----------|---------|-----------|
| **Docker** | `make docker-up` | Sobe todos os serviços |
| | `make docker-down` | Para todos os serviços |
| **Migrations** | `make migrate` | Roda migrations pendentes |
| | `make migrate-create MESSAGE="desc"` | Cria nova migration |
| | `make migrate-reset` | Drop + recria tudo (⚠️ dev only) |
| **Testes** | `make test` | Suite completa |
| | `make test-specific TESTS="path"` | Testes específicos |
| | `make test-cov` | Com cobertura |
| | `make test-reset` | Reseta banco de testes |
| **Lint** | `make lint` | black + ruff + mypy |
| | `make lint-fix` | Corrige formatação e imports |
| **Limpeza** | `make clean` | Remove caches (__pycache__, .mypy_cache etc.) |

### Limitações

- **Sem orquestrador de containers**: Não há Kubernetes, ECS, nem health monitoring automático em produção.
- **Secrets em .env**: Sem integração com vault (HashiCorp, AWS Secrets Manager etc.).
- **Sem CI/CD definido**: Pipeline de deploy não está no repositório.

### Melhorias possíveis

- [ ] **GitHub Actions pipeline**: lint → test → build image → push to registry → deploy.
- [ ] **Secrets manager**: Migrar de `.env` para AWS Secrets Manager / HashiCorp Vault.
- [ ] **Docker multi-stage build**: Imagem final menor, sem dev dependencies.
- [ ] **Terraform/Pulumi**: Infraestrutura como código para provisionar cloud resources.

---

## Módulo 3 — Camada de Dados

### Modelos do banco

O sistema tem **8 modelos** distribuídos em 6 arquivos em `src/db/models/`:

```
User (users)
├── UserProfile (user_profiles)       — 1:1
├── UserPreferences (user_preferences) — 1:1
├── Subscription (subscriptions)       — 1:1
├── Conversation (conversations)       — 1:N
│   └── Message (messages)             — 1:N
├── CalendarIntegration (calendar_integrations) — 1:N
│   └── CalendarEvent (calendar_events)         — 1:N
```

#### User

| Campo | Tipo | Nota |
|-------|------|------|
| id | UUID | PK, auto-gerado |
| email | String(255) | Unique, indexed |
| hashed_password | String(255) | bcrypt |
| full_name | String(255) | Nullable |
| is_admin | Boolean | Default False |
| is_blocked | Boolean | Default False |

**Evento automático**: Após `INSERT` em `users`, o ORM cria automaticamente `UserProfile`, `UserPreferences` e `Subscription(tier=FREE)`.

#### UserProfile

| Campo | Tipo | Nota |
|-------|------|------|
| onboarding_status | Enum | NOT_STARTED, IN_PROGRESS, COMPLETED |
| onboarding_current_step | String(50) | intro → name → frequency → routine → goals → calendar → closing |
| onboarding_data | JSONB | work_context, initial_state, initial_goals |
| preferred_name | String(100) | Definido no onboarding |
| vision_5_years | Text | Visão de longo prazo |
| annual_objectives | JSONB | Array de {description, life_area} |
| moral_profile | JSONB | Scores 0-1 por eixo moral |
| strengths | JSONB | Array de {description, category, source} |
| interests | JSONB | Array de {name, type, engagement_level} |
| satisfaction_* | Integer(1-10) | health, work, relationships, personal_time |

**Enums associados**: `OnboardingStatus`, `LifeArea`, `PatternType`, `StrengthCategory`, `StrengthSource`, `InterestType`, `EngagementLevel`.

#### UserPreferences

| Campo | Tipo | Default |
|-------|------|---------|
| timezone | String(50) | "UTC" |
| language | String(10) | "pt-BR" |
| communication_style | Enum | DIRECT (ou GENTLE, MOTIVATING) |
| contact_frequency | Enum | SOMETIMES (ou RARELY, FREQUENTLY) |
| coach_name | String(50) | "Virtus" |
| morning_checkin_enabled | Boolean | True |
| morning_checkin_time | Time | 08:00 |
| evening_checkin_enabled | Boolean | True |
| evening_checkin_time | Time | 21:00 |
| weekly_review_day | Enum WeekDay | SUNDAY |
| week_start_day | Enum WeekDay | MONDAY |

#### Conversation + Message

- **Conversation**: título, ai_provider, ai_model, system_prompt.
- **Message**: role (`user` | `assistant` | `system`), content (Text), tokens_used, meta (JSONB).

#### CalendarIntegration + CalendarEvent

- **CalendarIntegration**: provider (GOOGLE_CALENDAR, OUTLOOK, APPLE_CALENDAR), tokens encriptados com Fernet, status (PENDING → ACTIVE → TOKEN_EXPIRED → ERROR → DISCONNECTED).
- **CalendarEvent**: external_id, title, start_time, end_time, event_type inferido (MEETING, FOCUS, PERSONAL, TRAVEL, OTHER).

### Migrations (Alembic)

7 migrations versionadas em `alembic/versions/`:

| Data | Slug | O que faz |
|------|------|-----------|
| 2025-10-05 | initial_schemas | User, Conversation, Message, Profile, Preferences |
| 2026-01-02 | expand_user_profile | CalendarIntegration, CalendarEvent, campos JSONB no profile |
| 2026-01-11 | add_subscription | Subscription model com tiers |
| 2026-01-14 | add_onboarding_fields | onboarding_status, current_step, started/completed_at |
| 2026-01-15 | add_admin_fields | is_admin, is_blocked |
| 2026-01-27 | add_contact_frequency | ContactFrequency enum |
| 2026-02-01 | add_extra_data | onboarding_data JSONB, preferred_name |

### Session Management

```python
# src/db/session.py
AsyncEngine (cached via @lru_cache)
  └─ async_sessionmaker[AsyncSession]
       ├─ expire_on_commit=False   # objetos usáveis após commit
       ├─ autocommit=False         # transações manuais
       └─ autoflush=False          # flush explícito
```

A dependency `get_db()` do FastAPI fornece uma sessão por request via `async with` + `try/finally`.

### Limitações

- **Sem soft delete**: Registros são deletados fisicamente (`CASCADE`). Sem auditoria de deleções.
- **JSONB sem schema validation**: `onboarding_data`, `annual_objectives`, `strengths` etc. são JSON livre — validação é apenas na camada Python.
- **Sem índice em JSONB**: Queries dentro de campos JSONB seriam full-scan.
- **Sem particionamento**: Tabela `messages` vai crescer linearmente com o uso. Sem particionamento por data ou user.

### Melhorias possíveis

- [ ] **Soft delete com `deleted_at`**: Preservar histórico para auditoria.
- [ ] **JSON Schema validation no Postgres**: `CHECK` constraints com `jsonb_matches_schema()` (PG 17+).
- [ ] **GIN index em JSONB**: Para queries tipo `WHERE onboarding_data @> '{"work_context": "freelancer"}'`.
- [ ] **Particionamento de messages**: Por `created_at` (range partitioning mensal).
- [ ] **Read replicas**: Separar leitura de escrita para escalar queries.

---

## Módulo 4 — Autenticação e Segurança

### Fluxo de autenticação

```
REGISTER                          LOGIN
POST /auth/register               POST /auth/login
  │                                 │
  ▼                                 ▼
hash_password(bcrypt)             verify_password()
  │                                 │
  ▼                                 ▼
User criado no DB                 create_access_token(JWT)
                                  create_refresh_token(JWT)
                                    │
                                    ▼
                                  access_token → body
                                  refresh_token → HttpOnly cookie
```

### Password Hashing

```python
# src/core/security.py
BCRYPT_ROUNDS = 12  # 2^12 = 4096 iterações

def _preprocess_password(password: str) -> bytes:
    """SHA256 antes do bcrypt — contorna limite de 72 bytes."""
    return hashlib.sha256(password.encode()).hexdigest().encode()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(preprocessed, bcrypt.gensalt(rounds=12)).decode()
```

O pré-processamento com SHA256 é necessário porque bcrypt ignora silenciosamente bytes após o 72º — senhas longas teriam colisões sem este passo.

### JWT Tokens

| Token | Duração | Armazenamento | Conteúdo |
|-------|---------|---------------|----------|
| Access | 30 min | Header `Authorization: Bearer` | `{sub: user_id, type: "access", exp}` |
| Refresh | 7 dias | Cookie HttpOnly | `{sub: user_id, type: "refresh", exp}` |

**Rotação**: `POST /auth/refresh` gera novo par access+refresh e sobrescreve o cookie.

### OAuth2 (Google Calendar)

```
GET /api/v1/auth/google → authorization_url (Google consent screen)
  ↓
Usuário autoriza no Google
  ↓
GET /api/v1/auth/google/callback?code=...&state=...
  ↓
Troca code por tokens (access + refresh)
  ↓
Tokens encriptados com Fernet → salvos em CalendarIntegration
  ↓
Redirect para frontend com status=success
```

Os tokens OAuth são encriptados com `ENCRYPTION_KEY` (Fernet) antes de salvar no banco — nunca ficam em plaintext.

### Rate Limiting

Implementado via `slowapi`:

| Endpoint | Limite |
|----------|--------|
| `/auth/register` | 5/min |
| `/auth/login` | 5/min |
| `/me/profile` GET | 20/min |
| `/me/profile` PATCH | 10/min |
| `/me/preferences` GET | 20/min |
| `/me/preferences` PATCH | 10/min |
| `/me/subscription` GET | 20/min |

### Middleware Stack

Ordem de execução (de fora para dentro):

```
Request →
  1. CORSMiddleware          (headers de cross-origin)
  2. UserStateMiddleware      (extrai user_id para request.state)
  3. LoggingMiddleware        (loga request/response timing)
  4. Rate Limiting            (per-endpoint via slowapi)
→ Handler
```

### Dependency Injection

```python
# src/core/dependencies.py
get_current_user(token, db) → User
  ├─ Extrai JWT do header Bearer
  ├─ decode_token() → valida signature e expiry
  ├─ Verifica type == "access"
  ├─ Busca user por ID (cached 3min no Redis)
  └─ Verifica is_blocked == False

require_admin(user) → User  # checa user.is_admin
require_tier(min_tier) → User  # checa subscription.tier >= min_tier
```

### Limitações

- **Sem blacklist de tokens**: Logout não invalida o access token existente — ele permanece válido até expirar (30 min).
- **State do OAuth em memória**: Em `oauth.py`, o state token é guardado em dict Python — se o processo reiniciar, callbacks pendentes falham.
- **Sem 2FA/MFA**: Apenas email + password.
- **Sem rate limiting global**: Apenas per-endpoint; um atacante pode paralelizar requests a endpoints diferentes.

### Melhorias possíveis

- [ ] **Token blacklist no Redis**: Ao fazer logout, adicionar `jti` do token ao Redis com TTL = tempo restante.
- [ ] **State do OAuth no Redis**: Persistir state tokens no Redis com TTL de 10 minutos.
- [ ] **2FA via TOTP**: Adicionar segundo fator com Google Authenticator / Authy.
- [ ] **Rate limiting por IP global**: Limite de 100 req/min por IP independente do endpoint.
- [ ] **PKCE para OAuth**: Adicionar code_verifier/code_challenge para segurança extra.

---

## Módulo 5 — API REST

### Visão geral dos routers

| Router | Prefixo | Endpoints | Auth | Propósito |
|--------|---------|-----------|------|-----------|
| auth | `/auth` | 5 | Parcial | Register, login, refresh, logout, me |
| admin | `/admin` | 5 | Admin | CRUD de users, onboarding reset |
| oauth | `/api/v1/auth` | 2 | Sim | Google OAuth flow |
| chat | `/chat` | 7 | Sim | Conversations + messages |
| onboarding | `/api/v1/onboarding` | 2 | Sim | Status e skip |
| profile | `/api/v1/me/profile` | 2 | Sim | Get/update profile |
| preferences | `/api/v1/me/preferences` | 2 | Sim | Get/update preferences |
| subscription | `/api/v1/me/subscription` | 2 | Sim | Get/update subscription |
| calendar | `/api/v1/me/calendar` | 5 | Sim | Integrations + events |
| — | `/health_check` | 1 | Não | Health check |

**Total: ~33 endpoints**.

### Endpoint principal: Criar mensagem

```
POST /chat/conversations/{conversation_id}/messages

Request:
{
    "content": "Me chama de Marcos, trabalho como freelancer"
}

Response (201):
{
    "user_message": {
        "id": "uuid",
        "role": "user",
        "content": "Me chama de Marcos, trabalho como freelancer",
        "created_at": "2026-02-08T10:00:00Z"
    },
    "assistant_message": {
        "id": "uuid",
        "role": "assistant",
        "content": "Legal, Marcos! Vou salvar isso...",
        "meta": {
            "current_step": "name",
            "next_step": "frequency",
            "tool_rounds": 1
        },
        "created_at": "2026-02-08T10:00:02Z"
    }
}
```

Este é o endpoint que dispara todo o pipeline agentic (módulos 6-13).

### Padrão de schemas (Pydantic)

```
XxxCreate   → input para criação
XxxUpdate   → input para update (campos opcionais)
XxxRead     → output para leitura
XxxResponse → wrapper com metadados
XxxList     → lista paginada {items, total}
```

### Limitações

- **Sem paginação em messages**: `GET /conversations/{id}/messages` retorna todas as mensagens de uma vez.
- **Sem versionamento consistente**: Alguns routers usam `/api/v1/`, outros não.
- **Sem HATEOAS**: Respostas não incluem links para recursos relacionados.
- **Sem WebSocket**: Chat é request-response; sem push de atualizações.

### Melhorias possíveis

- [ ] **Cursor pagination em messages**: Paginar por `created_at` com cursor para suportar conversas longas.
- [ ] **Padronizar prefixo `/api/v1/`** em todos os routers.
- [ ] **WebSocket para chat**: Streaming de respostas token a token.
- [ ] **OpenAPI tags e exemplos**: Melhorar a documentação automática do Swagger.
- [ ] **API versioning**: Suporte a v1/v2 lado a lado para evoluir sem quebrar clientes.

---

## Módulo 6 — Serviço de Chat

### Localização: `src/services/chat.py`

Este é o **ponto de convergência** entre a camada REST e o sistema agentic.

### Fluxo detalhado de `create_message()`

```python
async def create_message(db, conversation_id, user_id, content):
    # 1. Verificar ownership da conversation
    conversation = await get_conversation_by_id(db, conversation_id, user_id)

    # 2. Criar mensagem do user no DB
    user_msg = Message(role="user", content=content, ...)
    db.add(user_msg)
    await db.commit()

    # 3. Buscar histórico de mensagens
    history = await _get_message_history(db, conversation_id)

    # 4. Obter resposta do agente
    response_text = await _route_agent_response(
        db=db,
        user_id=user_id,
        message=content,
        conversation_id=conversation_id,
        conversation_history=history,
    )

    # 5. Criar mensagem do assistant no DB
    assistant_msg = Message(role="assistant", content=response_text, ...)
    db.add(assistant_msg)
    await db.commit()

    # 6. Invalidar cache
    await invalidate_conversations_cache(user_id)

    return (user_msg, assistant_msg)
```

### `_route_agent_response()` — Bridge para o mundo agentic

```python
async def _route_agent_response(db, user_id, message, conversation_id, history):
    # Cria as dependências
    llm_service = get_ai_service("openai")
    context_adapter = _ContextServiceAdapter(db)  # wraps DB session

    # Factory e Router
    factory = AgentFactory(db, llm_service, context_adapter)
    router = AgentRouter(factory)

    # Delega para o sistema de agentes
    return await router.route(user_id, message, conversation_id, history)
```

### `_ContextServiceAdapter`

Padrão Adapter que wraps `AsyncSession` para expor a interface que `AgentRouter` espera:

```python
class _ContextServiceAdapter:
    async def build_permanent_context(self, user_id):
        return await context.build_permanent_context(self._db, user_id)
```

### AgentRouter (`src/services/agent_router.py`)

```python
class AgentRouter:
    async def route(self, user_id, message, conversation_id, history):
        # 1. Cria o orchestrator
        orchestrator = self.factory.create_orchestrator()

        # 2. Constrói contexto do usuário
        user_context = await self.factory.context_service.build_permanent_context(user_id)

        # 3. Orchestrator decide para onde rotear
        decision = await orchestrator.process(message, user_context, history)

        # 4. Se não há sub-agente, retorna resposta direta
        if not decision.next_agent:
            return decision.response

        # 5. Cria e executa o sub-agente
        agent = self.factory.create_agent(decision.next_agent)
        response = await agent.process(message, user_context, history)

        return response.response
```

### AgentFactory (`src/services/agent_factory.py`)

Factory que encapsula a criação de agentes com suas dependências:

```python
class AgentFactory:
    def create_orchestrator(self) -> OrchestratorAgent:
        return OrchestratorAgent(self.llm, ToolRegistry())

    def create_agent(self, name: str) -> BaseAgent:
        registry = self._get_registry(name)
        if name == "onboarding":
            return OnboardingAgent(self.llm, registry)
        elif name == "advisor":
            return AdvisorAgent(self.llm, registry)

    def _get_registry(self, name: str) -> ToolRegistry:
        """Registra as tools corretas para cada agente."""
        registry = ToolRegistry()
        if name == "onboarding":
            registry.register(SaveUserProfileTool(self.db))
            registry.register(SaveUserPreferencesTool(self.db))
            registry.register(CompleteOnboardingStepTool(self.db))
        elif name == "advisor":
            registry.register(GetCurrentDateTool())
            registry.register(GetUserPreferencesTool(self.db))
            registry.register(GetCalendarEventsTool(self.db))
        return registry
```

### Limitações

- **Sem conversation memory management**: O histórico completo é passado ao LLM a cada mensagem. Conversas longas vão exceder o context window.
- **Sem transaction rollback**: Se a chamada ao LLM falhar após salvar a mensagem do user, a mensagem fica orphan.
- **Response é string, não structured**: O retorno do agente é texto livre; metadados (step, tools) ficam apenas no meta.
- **Instanciação por request**: AgentFactory, Router, Registry são criados a cada mensagem. Sem pooling.

### Melhorias possíveis

- [ ] **Conversation summarization**: Quando histórico exceder N tokens, resumir mensagens antigas e manter apenas as K mais recentes.
- [ ] **Transação atômica**: Usar uma única transação para user_msg + llm_call + assistant_msg.
- [ ] **Structured response**: Retornar `AgentResponse` completo ao client (com metadata).
- [ ] **Singleton factory**: Cache registries e reuse entre requests.

---

## Módulo 7 — Sistema de Agentes

### Hierarquia

```
BaseAgent (ABC)
├── OrchestratorAgent    — Roteador (sem tools)
├── OnboardingAgent      — Conduz onboarding (3 tools)
└── AdvisorAgent         — Conversa livre (3 tools)
```

### BaseAgent (`src/agents/base.py`)

Classe abstrata que define o contrato e fornece funcionalidade comum:

```python
class BaseAgent(ABC):
    # === Propriedades abstratas ===
    @property @abstractmethod
    def name(self) -> str: ...

    @property @abstractmethod
    def skills(self) -> list[str]: ...

    @property @abstractmethod
    def available_tools(self) -> list[str]: ...

    # === Funcionalidade comum ===
    def load_skills(self) -> str
    def build_system_prompt(self, user_context) -> str
    def _get_tool_definitions(self) -> list[dict]
    def _build_messages(self, history, message) -> list[dict]

    # === Pipeline de processamento ===
    async def process(self, message, user_context, history) -> AgentResponse
    async def _run_tool_loop(self, *, messages, system_prompt, tool_definitions, max_rounds=3)
    async def _execute_tool_calls(self, executor, tool_calls) -> (assistant_msg, tool_msgs)

    # === Validação pós-execução ===
    def validate_tool_usage(self, tool_calls_made, user_context, message) -> str | None
```

**`AgentResponse`** — dataclass de retorno:

```python
@dataclass
class AgentResponse:
    response: str | None              # Texto para o usuário
    tool_calls: list[dict] | None     # Tools executadas (para metadata)
    next_agent: str | None            # Handoff para outro agente
    metadata: dict[str, Any]          # Observabilidade
```

### OrchestratorAgent (`src/agents/orchestrator.py`)

- **Papel**: Classificar intenção e rotear para o agente correto.
- **Skills**: persona_base, tom_ajuste, contexto_usuario, classificacao_intencao, roteamento.
- **Tools**: Nenhuma (`available_tools = []`).
- **Retorno**: `AgentResponse(next_agent="onboarding" | "advisor")`.

Lógica central: verifica `should_route_to_onboarding(context)` — se onboarding não está completo, roteia para OnboardingAgent.

### OnboardingAgent (`src/agents/onboarding.py`)

Detalhado no [Módulo 13](#módulo-13--onboarding-express).

### AdvisorAgent (`src/agents/advisor.py`)

- **Papel**: Responder perguntas abertas, explorar possibilidades.
- **Skills**: persona_base, tom_ajuste, contexto_usuario, conversacao_livre.
- **Tools**: `get_current_date`, `get_user_preferences`, `get_calendar_events`.

### Padrão de design: Template Method

```
BaseAgent.process()          ← define o fluxo geral
  ├─ build_system_prompt()   ← customizável por subclass
  ├─ _get_tool_definitions() ← filtrado por available_tools
  ├─ _run_tool_loop()        ← compartilhado
  └─ validate_tool_usage()   ← hook para subclasses
```

`OnboardingAgent` override `process()` completamente para adicionar:
- System prompt customizado por step
- State summary injection
- Confirmation threshold
- Step metadata no response

### Limitações

- **OrchestratorAgent como gatekeeper**: Toda mensagem passa pelo orchestrator, mesmo quando o onboarding está em progresso e o roteamento é óbvio.
- **Sem memory entre conversas**: Cada conversa começa do zero; não há long-term memory além do que está no DB.
- **AdvisorAgent é minimal**: Poucas tools; não consegue executar ações complexas.
- **Sem paralelismo de agentes**: Não há support para múltiplos agentes processando em paralelo.

### Melhorias possíveis

- [ ] **Fast-path routing**: Se onboarding está IN_PROGRESS, pular o orchestrator e ir direto ao OnboardingAgent.
- [ ] **Agent memory**: Implementar episodic memory — resumos de conversas anteriores incluídos no contexto.
- [ ] **Mais agentes especializados**: PlanningAgent, ReflectionAgent, HabitAgent etc.
- [ ] **Multi-agent collaboration**: Dois agentes gerando respostas em paralelo e um selector escolhendo a melhor.
- [ ] **Agent handoff com contexto**: Quando orchestrator delega, passar um resumo da classificação.

---

## Módulo 8 — Sistema de Skills

### Conceito

Skills são **instruções em Markdown** que definem o comportamento dos agentes. Ficam em `src/skills/` e são carregadas dinamicamente no system prompt.

### Estrutura de diretórios

```
src/skills/
├── shared/                          # Usadas por todos os agentes
│   ├── persona_base/
│   │   └── instructions.md          # Identidade do Virtus
│   ├── tom_ajuste/
│   │   └── instructions.md          # Como adaptar tom
│   └── contexto_usuario/
│       └── instructions.md          # Como usar contexto permanente
│
├── orchestrator/
│   ├── classificacao_intencao/
│   │   └── instructions.md          # 9 tipos de intenção
│   └── roteamento/
│       └── instructions.md          # Regras de roteamento
│
├── onboarding/
│   ├── onboarding_express/
│   │   └── instructions.md          # 7 etapas detalhadas
│   └── extracao_preferencias/
│       └── instructions.md          # Extrair dados de texto livre
│
└── advisor/
    └── conversacao_livre/
        └── instructions.md          # Diretivas para conversa aberta
```

### Como as skills são carregadas

```python
# BaseAgent.load_skills()
def load_skills(self) -> str:
    skill_contents = []
    for skill_name in self.skills:  # ex: ["shared/persona_base", "onboarding/onboarding_express"]
        path = self._skills_path / skill_name / "instructions.md"
        skill_contents.append(path.read_text())
    return "\n\n---\n\n".join(skill_contents)
```

### Exemplos de conteúdo

**persona_base** — define a identidade:
```markdown
# Persona Base - Virtus

## Identidade
Você é o **Virtus**, um mentor profissional compassivo...

## Pilares de Personalidade
### 1. Empático sem ser Piegas
| Faz | Não Faz |
| Reconhece dificuldades com naturalidade | Dramatiza ou exagera emoções |

### 2. Direto sem ser Frio
...
```

**classificacao_intencao** — taxonomia de intenções:
```markdown
9 tipos: ONBOARDING_NEEDED, GREETING, PLANNING_REQUEST,
         CHECKIN_RESPONSE, EMOTIONAL_SHARING, HELP_REQUEST,
         FEEDBACK, FREE_CHAT, OUT_OF_SCOPE
```

### Por que Markdown?

- **Versionável**: Mudanças de comportamento são diffs no Git, não código.
- **Legível**: Product managers e designers conseguem ler e editar.
- **Modular**: Adicionar uma skill = criar uma pasta + arquivo.
- **Sem deploy**: Mudar comportamento do agente sem alterar código Python.

### Limitações

- **Sem hierarquia de prioridade**: Se duas skills dão instruções conflitantes, o LLM decide qual seguir.
- **Sem template variables**: O conteúdo é estático; não há `{{user_name}}` dentro do Markdown.
- **Sem validação**: Não há schema ou linter para skills — um typo no nome do arquivo causa `FileNotFoundError` em runtime.
- **Sem versionamento por agente**: Não há como ter v1 e v2 de uma mesma skill rodando em paralelo.

### Melhorias possíveis

- [ ] **Template engine**: Usar Jinja2 para variáveis dentro das skills (`{{user_name}}`, `{{current_step}}`).
- [ ] **Skill validation CLI**: `make validate-skills` que verifica que todas as skills referenciadas existem.
- [ ] **A/B testing de skills**: Carregar versões diferentes para grupos de usuários.
- [ ] **Priority/weight system**: Skills com prioridade explícita para resolver conflitos.
- [ ] **Skill registry**: Catálogo centralizado com metadata (autor, versão, agentes que usam).

---

## Módulo 9 — Sistema de Tools

### Conceito

Tools são **funções executáveis** que os agentes podem chamar via LLM function calling. Cada tool tem:
- Nome único
- Descrição (para o LLM entender quando usar)
- Schema de parâmetros (JSONSchema)
- Método `execute()` async

### Arquitetura

```
BaseTool (ABC)
  ├─ to_tool_definition() → formato OpenAI function calling
  └─ execute(args) → ToolResult

ToolRegistry
  ├─ register(tool)
  ├─ get_tool(name) → BaseTool
  └─ list_tools() → [metadata]

ToolExecutor
  ├─ execute(name, args) → ToolResult
  └─ wraps error handling + logging
```

### BaseTool (`src/tools/base.py`)

```python
class BaseTool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]  # JSONSchema

    async def execute(self, args: dict[str, Any]) -> ToolResult: ...

    def to_tool_definition(self) -> dict:
        """Formato OpenAI function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

@dataclass
class ToolResult:
    success: bool
    data: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "error": self.error}
```

### Tools disponíveis

| Tool | Agente | Parâmetros | Efeito |
|------|--------|------------|--------|
| `save_user_profile` | Onboarding | user_id, preferred_name?, onboarding_data? | UPDATE user_profiles |
| `save_user_preferences` | Onboarding | user_id, contact_frequency?, timezone? | UPDATE user_preferences |
| `complete_onboarding_step` | Onboarding | user_id, step | Avança step; closing → COMPLETED |
| `get_current_date` | Advisor | timezone?, format? | Retorna datetime |
| `get_user_preferences` | Advisor | user_id | SELECT user_preferences |
| `get_calendar_events` | Advisor | user_id, days_ahead?, limit? | SELECT calendar_events |

### ToolRegistry (`src/tools/registry.py`)

Pattern Registry — mapeia `name → BaseTool`:

```python
class ToolRegistry:
    _tools: dict[str, BaseTool]

    def register(self, tool: BaseTool) -> None
    def get_tool(self, name: str) -> BaseTool | None
    def unregister(self, name: str) -> None
    def list_tools(self) -> list[dict]
    def get_tool_definitions(self) -> list[dict]
```

Cada agente tem sua **própria instância** de ToolRegistry, criada pela `AgentFactory`. Isso garante isolamento — OnboardingAgent não tem acesso a `get_calendar_events`.

### ToolExecutor (`src/tools/executor.py`)

Wrapper de execução segura:

```python
class ToolExecutor:
    async def execute(self, tool_name: str, args: dict) -> ToolResult:
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_name}' not found")
        return await tool.execute(args)
```

### Como o LLM chama tools

1. Agent envia `tools=[{type: "function", function: {name, description, parameters}}]` ao LLM
2. LLM retorna `tool_calls=[{id: "call_xyz", name: "save_user_profile", arguments: {...}}]`
3. `_execute_tool_calls()` executa cada call via ToolExecutor
4. Resultados voltam como mensagens `{role: "tool", content: json_result, tool_call_id: "call_xyz"}`
5. LLM recebe os resultados e continua (texto ou mais tool calls)

### Limitações

- **Sem timeouts por tool**: Se uma tool travar (ex: query lenta), não há timeout — bloqueia todo o loop.
- **Sem retry por tool**: Tool falha → resultado de erro vai ao LLM. O multi-round loop pode compensar, mas não há retry explícito.
- **Sem permissions/scoping**: Uma tool com acesso ao DB pode ler/escrever qualquer coisa. Sem row-level security.
- **Sem async parallelism**: Múltiplas tool_calls no mesmo round são executadas sequencialmente.

### Melhorias possíveis

- [ ] **Timeout por tool**: `asyncio.wait_for(tool.execute(args), timeout=10)`.
- [ ] **Parallel tool execution**: `asyncio.gather(*[executor.execute(tc) for tc in tool_calls])`.
- [ ] **Tool permissions**: Cada tool declara quais scopes precisa; verificar contra user tier.
- [ ] **Tool usage analytics**: Registrar quais tools são chamadas, frequência, tempo de execução.
- [ ] **Dry-run mode**: Executar tools em modo simulação para testes end-to-end sem side effects.

---

## Módulo 10 — Multi-Round Tool Loop

### Evolução do design

O loop original era **single-round**:
```
LLM → tool_calls → execute → LLM (forçado texto, tools=[]) → resposta
```

Problemas:
- Tool falha → agente responde fingindo que funcionou
- Usuário dá 5 dados numa mensagem → só 1 é processado
- Sem verificação de que tools obrigatórias foram chamadas

### Solução: Hybrid Smart Tool Loop (4 camadas)

#### Camada 1 — Multi-Round (até 3 rounds)

```
Round 1: LLM → tool_calls → execute → results
Round 2: LLM (com results + tools) → tool_calls → execute → results
Round 3: LLM (com results + tools) → text response ✓
Fallback: max_rounds atingido → 1 call final com tools=[] forçando texto
```

```python
async def _run_tool_loop(self, *, messages, system_prompt, tool_definitions, max_rounds=3):
    current_messages = list(messages)
    executor = ToolExecutor(self.tools)
    all_tool_calls = []
    tool_rounds = 0

    for _round in range(max_rounds):
        result = await self.llm.generate_response_with_tools(
            messages=current_messages,
            system_prompt=system_prompt,
            tools=tool_definitions,
        )

        tool_calls = result.get("tool_calls")
        if not tool_calls:
            return AgentResponse(response=result["content"], metadata={"tool_rounds": tool_rounds})

        tool_rounds += 1
        all_tool_calls.extend(tool_calls)
        assistant_msg, tool_messages = await self._execute_tool_calls(executor, tool_calls)
        current_messages = [*current_messages, assistant_msg, *tool_messages]

    # Força texto
    followup = await self.llm.generate_response_with_tools(
        messages=current_messages, system_prompt=system_prompt, tools=[]
    )
    return AgentResponse(response=followup["content"], metadata={"tool_rounds": tool_rounds})
```

#### Camada 2 — State Injection

O sistema prompt inclui um resumo do estado atual do banco:

```
## Estado Atual no Banco de Dados
- preferred_name: Marcos
- onboarding_data.work_context: (não definido)
- onboarding_data.initial_state: (não definido)
- contact_frequency: RARELY
- timezone: America/Sao_Paulo
- current_step: routine (steps concluídos: intro, name, frequency)

IMPORTANTE: Se o usuário já forneceu dados marcados como '(não definido)',
você DEVE usar as tools para salvá-los antes de responder.
```

Isso permite ao LLM saber o que já está salvo e o que falta.

#### Camada 3 — Post-Execution Validation

Após `_run_tool_loop`, uma validação determinística verifica se tools obrigatórias foram chamadas:

```python
# BaseAgent — hook padrão (no-op)
def validate_tool_usage(self, tool_calls_made, user_context, message) -> str | None:
    return None

# OnboardingAgent — override com regras por step
def validate_tool_usage(self, tool_calls_made, user_context, message) -> str | None:
    current_step = self.get_current_step(user_context)
    tool_names = {tc.get("name") for tc in tool_calls_made}

    if current_step == "name" and len(message) > 3:
        if "save_user_profile" not in tool_names:
            return "CORREÇÃO: save_user_profile não foi chamada. Chame agora."

    if current_step == "closing":
        if "complete_onboarding_step" not in tool_names:
            return "CORREÇÃO: complete_onboarding_step não foi chamada."

    return None
```

Se retorna correção → executa um **retry** com `max_rounds=2`.

#### Camada 4 — Confirmation Threshold

Se o usuário envia muitos dados de uma vez (≥ 5 categorias), o sistema injeta:

```
## CONFIRMAÇÃO NECESSÁRIA
O usuário forneceu muitos dados de uma vez. ANTES de salvar, liste os dados
extraídos e peça confirmação. Só chame as tools DEPOIS da confirmação.
```

Categorias detectadas por keyword matching:
- **nome**: "chama de", "meu nome"
- **timezone**: "fuso", "são paulo", "brasília"
- **trabalho**: "freelancer", "clt", "estudante"
- **frequência**: "frequente", "raramente"
- **goals**: "objetivo", "meta", "produtiv"

### Diagrama do fluxo completo

```
process()
  │
  ├─ build system prompt (com state summary + confirmation se necessário)
  │
  ├─ _run_tool_loop(max_rounds=3)
  │   ├─ Round 1: LLM → tools? → execute
  │   ├─ Round 2: LLM → tools? → execute
  │   └─ Round 3: LLM → text ou force text
  │
  ├─ validate_tool_usage()
  │   ├─ None → retorna resposta
  │   └─ "CORREÇÃO: ..." → retry
  │       └─ _run_tool_loop(max_rounds=2)
  │
  └─ return AgentResponse
```

### Limitações

- **Keyword matching é frágil**: `_count_data_points()` usa keywords fixos; sinônimos não cobertos.
- **Validation é por step, não por dados**: Valida se a tool foi chamada, não se os dados corretos foram passados.
- **Retry único**: Apenas 1 retry após validation failure; se o LLM falhar de novo, aceita o resultado.
- **Sem rollback de tools**: Se round 1 executa uma tool com dados errados e round 2 corrige, ambas execuções ficam no DB.

### Melhorias possíveis

- [ ] **NLP-based data point detection**: Usar o próprio LLM para contar/classificar dados em vez de keywords.
- [ ] **Data validation layer**: Verificar não só se a tool foi chamada, mas se os argumentos passados são válidos.
- [ ] **Idempotent tools**: Tools que fazem merge/upsert em vez de overwrite, permitindo retries seguros.
- [ ] **Configurable max_rounds**: Permitir que cada agente defina seu próprio limite de rounds.
- [ ] **Circuit breaker**: Se muitos retries acontecem, desabilitar validation e alertar.

---

## Módulo 11 — Contexto Permanente

### Localização: `src/services/context.py`

### Propósito

Toda vez que um agente processa uma mensagem, o sistema monta um **snapshot completo** do estado do usuário no banco. Esse contexto é incluído no system prompt para que o LLM saiba quem é o usuário.

### Estrutura do contexto

```python
{
    "user": {
        "id": "uuid-string",
        "email": "user@example.com",
        "full_name": "José Silva"
    },
    "preferences": {
        "timezone": "America/Sao_Paulo",
        "language": "pt-BR",
        "communication_style": "DIRECT",
        "contact_frequency": "SOMETIMES",
        "coach_name": "Virtus",
        "checkin_settings": {
            "morning_enabled": True,
            "morning_time": "08:00:00",
            "evening_enabled": True,
            "evening_time": "21:00:00"
        },
        "weekly_review_day": "SUNDAY",
        "week_start_day": "MONDAY"
    },
    "profile": {
        "onboarding_status": "IN_PROGRESS",
        "onboarding_current_step": "routine",
        "onboarding_data": {"work_context": "freelancer"},
        "preferred_name": "Zé",
        "vision_5_years": None,
        "annual_objectives": None,
        "strengths": None,
        "interests": None,
        "life_satisfaction": {"health": 7, "work": 5, ...}
    },
    "calendar_integration": {
        "connected": True,
        "providers": [{"provider": "GOOGLE_CALENDAR", "status": "ACTIVE", ...}]
    }
}
```

### Como o contexto é consumido

1. **BaseAgent._format_context()**: converte dict → texto legível para o system prompt.
2. **OnboardingAgent.build_state_summary()**: extrai campos específicos do onboarding e mostra o que está salvo vs. faltando.

### Simplificação para IA

`_build_profile_context()` transforma estruturas JSONB complexas em formatos simplificados:

```python
# Strengths: de 8+ campos para 2
strengths_simplified = [
    {"description": s["description"], "category": s["category"]}
    for s in profile.strengths
]

# Interests: de 6+ campos para 3
interests_simplified = [
    {"name": i["name"], "type": i["type"], "engagement_level": i["engagement_level"]}
    for i in profile.interests
]
```

### Segurança

**NUNCA** incluir no contexto:
- OAuth tokens (access_token, refresh_token)
- Hashed passwords
- Encryption keys
- Internal IDs desnecessários

### Limitações

- **Query a cada mensagem**: 4 SELECTs (User, Profile, Preferences, CalendarIntegration) por mensagem. Sem cache.
- **Contexto completo sempre**: Não há filtragem — mesmo dados irrelevantes para a conversa atual são incluídos.
- **Sem diff**: O agente não sabe o que mudou desde a última mensagem; recebe sempre o snapshot completo.

### Melhorias possíveis

- [ ] **Cache de contexto no Redis**: TTL de 1-2 minutos; invalidar quando tools fazem writes.
- [ ] **Context relevance filtering**: Só incluir seções relevantes ao agente atual (onboarding não precisa de calendar).
- [ ] **Delta context**: Incluir um diff do que mudou desde a última mensagem.
- [ ] **Lazy loading**: Carregar calendar_events sob demanda (via tool) em vez de no contexto.

---

## Módulo 12 — Integração com LLMs

### Abstração de providers (`src/services/ai/`)

```python
class BaseAIService(ABC):
    async def generate_response(
        self, messages, model, system_prompt
    ) -> str

    async def generate_response_with_tools(
        self, messages, system_prompt, tools, tool_choice="auto", model="gpt-4o-mini"
    ) -> dict  # {content, tool_calls, finish_reason}
```

### OpenAIService (`src/services/ai/openai_service.py`)

**Provider principal** — único com suporte a function calling.

**Retry logic** via `tenacity`:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
)
async def _call_openai(self, ...):
    ...
```

**Formato de tool calls (OpenAI → interno)**:
```python
# OpenAI retorna:
{
    "id": "call_abc123",
    "type": "function",
    "function": {"name": "save_user_profile", "arguments": '{"preferred_name": "Zé"}'}
}

# Transformado para:
{
    "id": "call_abc123",
    "type": "function",
    "name": "save_user_profile",
    "arguments": {"preferred_name": "Zé"}  # parsed de JSON string para dict
}
```

### AnthropicService (`src/services/ai/anthropic_service.py`)

**Provider secundário** — apenas `generate_response()` implementado. `generate_response_with_tools()` levanta `NotImplementedError`.

### Factory

```python
def get_ai_service(provider: str) -> BaseAIService:
    if provider == "openai":
        return OpenAIService()
    elif provider == "anthropic":
        return AnthropicService()
```

### Limitações

- **OpenAI-only para agentes**: Anthropic não suporta function calling neste codebase.
- **Sem fallback entre providers**: Se OpenAI falha (rate limit, downtime), não tenta Anthropic.
- **Modelo hardcoded**: `gpt-4o-mini` como default; sem A/B testing de modelos.
- **Sem token counting**: Não há verificação de que messages + tools + system prompt cabem no context window.
- **Sem cost tracking**: Não rastreia custo por request/conversation/user.

### Melhorias possíveis

- [ ] **Anthropic function calling**: Implementar usando a Anthropic Tool Use API.
- [ ] **Provider fallback chain**: OpenAI → Anthropic → local model.
- [ ] **Token budget management**: Contar tokens antes de enviar; truncar histórico se necessário.
- [ ] **Cost tracking**: Registrar tokens usados por request; alertas de custo por user/dia.
- [ ] **Model routing**: Usar modelo leve (gpt-4o-mini) para routing, modelo pesado (gpt-4o) para respostas complexas.
- [ ] **Structured outputs**: Usar `response_format: {type: "json_schema"}` para respostas estruturadas.

---

## Módulo 13 — Onboarding Express

### Fluxo de 7 etapas

```
intro → name → frequency → routine → goals → calendar → closing
  │       │        │          │         │        │          │
  │       │        │          │         │        │          └─ COMPLETED
  │       │        │          │         │        └─ Oferece integração
  │       │        │          │         └─ initial_state + initial_goals
  │       │        │          └─ timezone + work_context
  │       │        └─ RARELY | SOMETIMES | FREQUENTLY (obrigatório)
  │       └─ preferred_name
  └─ Apresentação + confirmação
```

### O que cada etapa coleta e salva

| Step | Dados coletados | Tool chamada | Campo no DB |
|------|----------------|--------------|-------------|
| intro | Confirmação para começar | `complete_onboarding_step` | onboarding_current_step → "name" |
| name | Nome preferido | `save_user_profile` + `complete_onboarding_step` | preferred_name |
| frequency | Frequência de contato | `save_user_preferences` + `complete_onboarding_step` | contact_frequency |
| routine | Timezone + trabalho | `save_user_preferences` + `save_user_profile` + `complete_onboarding_step` | timezone, onboarding_data.work_context |
| goals | Estado atual + objetivos | `save_user_profile` + `complete_onboarding_step` | onboarding_data.initial_state, initial_goals |
| calendar | Decisão sobre integração | `complete_onboarding_step` | (nenhum dado novo) |
| closing | Encerramento | `complete_onboarding_step` | onboarding_status → COMPLETED |

### Serviço de Onboarding (`src/services/onboarding.py`)

Gerencia a state machine:

```python
async def start_onboarding(db, user_id):
    profile.onboarding_status = IN_PROGRESS
    profile.onboarding_started_at = now()
    profile.onboarding_current_step = "intro"

async def advance_step(db, user_id, current_step):
    next_step = ONBOARDING_STEPS[ONBOARDING_STEPS.index(current_step) + 1]
    profile.onboarding_current_step = next_step

async def complete_onboarding(db, user_id):
    profile.onboarding_status = COMPLETED
    profile.onboarding_completed_at = now()

async def skip_onboarding(db, user_id):
    # Pula direto para COMPLETED
```

**Session timeout**: Se onboarding está IN_PROGRESS por > 7 dias → reset para NOT_STARTED.

### System Prompt por step

O `OnboardingAgent._build_onboarding_prompt()` monta:

```
[Skills: persona_base + tom_ajuste + contexto_usuario + onboarding_express + extracao_preferencias]

---

## Situação Atual
**Etapa atual**: name
**Nome do usuário**: (ainda não definido)
**User ID para tools**: uuid-123

## Etapa NAME
Pergunte como o usuário prefere ser chamado...
Quando responder, chame save_user_profile com preferred_name...

## Estado Atual no Banco de Dados
- preferred_name: (não definido)
- onboarding_data.work_context: (não definido)
- contact_frequency: (não definido)
...
IMPORTANTE: Se o usuário já forneceu dados marcados como '(não definido)',
você DEVE usar as tools para salvá-los antes de responder.

## Instruções Importantes
1. Mantenha um tom acolhedor e conversacional
2. Extraia os dados necessários da resposta do usuário
3. Use as tools disponíveis para salvar os dados extraídos
...
```

### Validação por step

| Step | Regra de validação |
|------|-------------------|
| name | Mensagem > 3 chars → `save_user_profile` obrigatório |
| frequency | Keywords de frequência detectadas → `save_user_preferences` obrigatório |
| routine | Keywords de timezone → `save_user_preferences`; keywords de trabalho → `save_user_profile` |
| closing | `complete_onboarding_step` sempre obrigatório |

### Limitações

- **Fluxo linear rígido**: Não permite voltar a um step anterior ou pular steps intermediários (exceto `skip_onboarding` que pula tudo).
- **Sem persistência parcial**: Se o user diz nome + frequência na mesma mensagem, mas está no step "name", só nome é processado naquele step.
- **Sem timeout de inatividade**: Diferente do session timeout (7 dias), não há detecção de "user ficou 5 minutos sem responder".
- **Sem analytics**: Não rastreia taxa de conclusão por step, drop-off points, tempo médio por step.

### Melhorias possíveis

- [ ] **Fluxo não-linear**: Permitir avançar múltiplos steps numa única mensagem quando o user fornece dados suficientes.
- [ ] **Step rollback**: "Quero mudar meu nome" → voltar ao step name sem resetar tudo.
- [ ] **Inactivity nudge**: Se 24h sem resposta durante onboarding, enviar reminder.
- [ ] **Onboarding analytics**: Dashboard com funil de conversão por step.
- [ ] **Onboarding deep**: Fluxo expandido pós-express para coletar visão de 5 anos, satisfação por área etc.

---

## Módulo 14 — Observabilidade e Cache

### Logging

Logging estruturado via `logging` stdlib:

```python
logger = logging.getLogger(__name__)
logger.info(f"Processing onboarding message for step: {current_step}")
logger.error(f"Error in onboarding process: {e}", exc_info=True)
```

`LoggingMiddleware` registra cada request:
- Method + path
- Status code
- Tempo de processamento

### Redis Cache

Decorator `@redis_cache_decorator` aplicado em:

| Função | TTL | Invalidação |
|--------|-----|-------------|
| `_get_user_by_id()` | 3 min | Automática por expiração |
| `get_user_conversations()` | 5 min | `invalidate_conversations_cache()` após write |
| `get_conversation_messages()` | 5 min | Após criar mensagem |
| `list_ai_providers()` | 1 hora | Automática |

**Prefixo**: Configurável via `CACHE_PREFIX` (default: `app_cache`).

### Metadata em AgentResponse

Cada resposta de agente inclui metadata de observabilidade:

```python
metadata = {
    "finish_reason": "stop",       # Como o LLM parou
    "tool_rounds": 2,              # Quantos rounds de tools
    "tool_calls": [...],           # Quais tools foram chamadas
    "current_step": "name",        # Step do onboarding (se aplicável)
    "next_step": "frequency",      # Próximo step
}
```

### Limitações

- **Sem structured logging**: Logs são strings formatadas, não JSON estruturado.
- **Sem distributed tracing**: Sem correlation IDs entre requests, agentes e tools.
- **Sem métricas**: Sem Prometheus/Datadog para latência, throughput, error rates.
- **Sem alerting**: Sem notificação quando erros excedem threshold.

### Melhorias possíveis

- [ ] **Structured JSON logging**: `structlog` com campos padronizados (request_id, user_id, agent, tool).
- [ ] **OpenTelemetry**: Tracing distribuído com spans por agente, tool call, LLM request.
- [ ] **Prometheus metrics**: Contadores e histogramas para latência de LLM, tool execution, cache hit/miss.
- [ ] **Grafana dashboards**: Visualização de métricas em tempo real.
- [ ] **Error alerting**: Slack/PagerDuty quando error rate > threshold.

---

## Módulo 15 — Testes e Qualidade

### Estratégia TDD

O projeto segue **RED → GREEN → REFACTOR → CONNECT**:

1. **RED**: Escrever testes que falham para a funcionalidade nova.
2. **GREEN**: Implementar o mínimo para os testes passarem.
3. **REFACTOR**: Melhorar a implementação sem quebrar testes.
4. **CONNECT**: Rodar suite completa + lint para garantir integração.

### Estrutura de testes

```
tests/
├── agents/
│   ├── test_base_agent.py        # BaseAgent, multi-round loop, validation
│   ├── test_orchestrator_agent.py # Routing logic
│   ├── test_onboarding_agent.py  # 7 steps, state summary, confirmation
│   └── test_advisor_agent.py     # Free conversation
├── tools/
│   └── test_onboarding_tools.py  # SaveProfile, SavePreferences, CompleteStep
├── test_auth.py                  # Register, login, JWT
├── test_chat.py                  # Conversations, messages
├── test_context.py               # build_permanent_context
├── test_onboarding_service.py    # State machine
├── test_*.py                     # Outros módulos
└── conftest.py                   # Fixtures globais
```

**Total**: 465 testes.

### Comandos

```bash
make test                          # Suite completa
make test-specific TESTS=path      # Teste específico (TDD cycles)
make test-cov                      # Com cobertura
make lint                          # black + ruff + mypy
```

### Padrões de teste

**Mock do LLM**:
```python
self.mock_llm.generate_response_with_tools = AsyncMock(
    side_effect=[
        {"content": None, "tool_calls": [...], "finish_reason": "tool_calls"},
        {"content": "Response", "tool_calls": None, "finish_reason": "stop"},
    ]
)
```

**Conftest global**: Mock de `get_ai_service` — quando testar o path do orchestrator, mockar `_get_orchestrator_response` em vez do LLM.

### Quality gates

| Check | Tool | Rigor |
|-------|------|-------|
| Formatação | black (line-length=100) | Zero tolerance |
| Linting | ruff (E, W, F, I, B, C4, UP) | Zero tolerance |
| Tipagem | mypy (strict=true) | Zero tolerance |
| Testes | pytest (465 tests) | 100% pass |

### Limitações

- **Sem coverage enforcement**: Não há threshold mínimo de cobertura (ex: 80%).
- **Sem integration tests**: Testes usam mocks; não testam integração real com PostgreSQL/OpenAI.
- **Sem load/performance tests**: Não há benchmark de latência ou throughput.
- **Sem mutation testing**: Não valida que testes realmente detectam bugs (vs. apenas cobrem linhas).

### Melhorias possíveis

- [ ] **Coverage mínimo 80%**: `pytest --cov --cov-fail-under=80`.
- [ ] **Integration test suite**: Testes contra banco real e API real (OpenAI com modelo barato).
- [ ] **E2E tests**: Simular fluxo completo: register → login → onboarding 7 steps → chat.
- [ ] **Load testing**: Locust ou k6 para simular carga concorrente.
- [ ] **Mutation testing**: `mutmut` para validar qualidade dos testes.

---

## Módulo 16 — Padrões de Projeto

### Catálogo

| Pattern | Onde | Por quê |
|---------|------|---------|
| **Abstract Factory** | `AgentFactory` | Cria agentes + registries com dependências corretas |
| **Strategy** | `BaseAgent` + subclasses | Cada agente implementa seu próprio comportamento |
| **Template Method** | `BaseAgent.process()` | Fluxo padrão com hooks customizáveis (`validate_tool_usage`) |
| **Registry** | `ToolRegistry` | Lookup dinâmico de tools por nome |
| **Adapter** | `_ContextServiceAdapter` | Adapta DB session → interface de context service |
| **Decorator** | `@redis_cache_decorator` | Cross-cutting caching sem modificar funções |
| **Dependency Injection** | FastAPI `Depends()` | Loose coupling de componentes (db, auth, user) |
| **Builder** | `build_system_prompt()`, `_build_onboarding_prompt()` | Construção passo-a-passo de prompts complexos |
| **Chain of Responsibility** | Middleware stack | CORS → UserState → Logging → RateLimit |
| **Observer** | SQLAlchemy events (after_insert) | Auto-criar Profile/Preferences após User insert |
| **Singleton** | `@lru_cache` em engine/settings | Uma única instância compartilhada |
| **Facade** | `chat_service.create_message()` | Interface simples para fluxo complexo (DB + LLM + agents) |

### Padrões arquiteturais

| Pattern | Implementação |
|---------|---------------|
| **Layered Architecture** | API → Services → Agents/Tools → DB |
| **Repository-like** | Services encapsulam queries SQLAlchemy |
| **CQRS-like** | Tools de read (get_*) vs. write (save_*) separadas |
| **Event-driven (parcial)** | SQLAlchemy events; sem event bus |
| **Plugin Architecture** | Skills como plugins de Markdown; Tools como plugins executáveis |

---

## Módulo 17 — Limitações Arquiteturais e Roadmap

### Débitos técnicos consolidados

| Área | Débito | Impacto | Esforço |
|------|--------|---------|---------|
| **Streaming** | Respostas não são streamed | UX ruim (espera 3-10s) | Alto |
| **Context window** | Histórico completo a cada msg | Falha em conversas longas | Médio |
| **Provider lock-in** | Apenas OpenAI com tools | Sem fallback | Médio |
| **Observabilidade** | Logs simples, sem tracing | Difícil debugar em prod | Médio |
| **CI/CD** | Inexistente | Deploy manual | Médio |
| **Token tracking** | Sem contagem de custos | Surpresas na fatura | Baixo |
| **Test coverage** | Sem enforcement | Regressões possíveis | Baixo |
| **Soft delete** | Tudo é hard delete | Sem auditoria | Baixo |

### Roadmap sugerido por prioridade

#### P0 — Crítico para produção
1. **CI/CD pipeline**: GitHub Actions com lint → test → build → deploy.
2. **Streaming (SSE)**: Respostas token a token para reduzir latência percebida.
3. **Conversation summarization**: Truncar histórico quando exceder context window.
4. **Token tracking e alertas**: Registrar custo por request; alertar anomalias.

#### P1 — Alta prioridade
5. **Structured logging (structlog)**: JSON logs com correlation IDs.
6. **OpenTelemetry**: Tracing distribuído para debugar latência.
7. **Redis cache para contexto**: Evitar 4 queries por mensagem.
8. **Anthropic tool use**: Segundo provider com function calling.
9. **Coverage ≥ 80%**: Enforcement no CI.

#### P2 — Melhoria significativa
10. **Novos agentes**: PlanningAgent, ReflectionAgent, HabitTrackingAgent.
11. **Onboarding não-linear**: Processar múltiplos steps por mensagem.
12. **Agent memory**: Resumos de conversas anteriores no contexto.
13. **Parallel tool execution**: `asyncio.gather` para tool calls simultâneas.
14. **Integration tests**: Testes end-to-end contra banco real.

#### P3 — Nice to have
15. **A/B testing de skills**: Versões diferentes para diferentes users.
16. **Skill template engine (Jinja2)**: Variáveis dinâmicas dentro de skills.
17. **Multi-tenant**: Isolamento de dados entre organizações.
18. **WhatsApp channel**: Segundo canal de comunicação.
19. **Grafana dashboards**: Visualização de métricas.
20. **Mutation testing**: Validar qualidade dos testes.

---

## Apêndice A — Glossário

| Termo | Definição |
|-------|-----------|
| **Agent** | Componente autônomo que processa mensagens usando LLM + tools |
| **Skill** | Arquivo Markdown com instruções comportamentais para um agente |
| **Tool** | Função executável que um agente pode chamar via LLM function calling |
| **Tool Loop** | Ciclo iterativo: LLM → tool calls → execute → results → LLM |
| **Orchestrator** | Agente que classifica intenção e roteia para sub-agentes |
| **Handoff** | Delegação de um agente para outro via `next_agent` |
| **Context** | Snapshot do estado do usuário no banco, incluído no system prompt |
| **State Injection** | Inclusão do estado atual do DB no prompt para guiar o LLM |
| **Validation** | Verificação determinística pós-tool-loop de que tools obrigatórias foram chamadas |
| **Confirmation Threshold** | Mecanismo que pede confirmação quando muitos dados são fornecidos de uma vez |
| **Function Calling** | Capacidade do LLM de retornar chamadas de função estruturadas |

## Apêndice B — Referências rápidas

### Como adicionar um novo agente

1. Criar `src/agents/novo_agent.py` herdando de `BaseAgent`
2. Implementar `name`, `skills`, `available_tools`
3. Criar skills em `src/skills/novo_agent/`
4. Registrar tools na `AgentFactory._get_registry()`
5. Adicionar rota no `OrchestratorAgent` (skill de roteamento)
6. Escrever testes em `tests/agents/test_novo_agent.py`

### Como adicionar uma nova tool

1. Criar classe em `src/tools/` herdando de `BaseTool`
2. Definir `name`, `description`, `parameters` (JSONSchema)
3. Implementar `async execute(args) -> ToolResult`
4. Registrar na `AgentFactory._get_registry()` para o agente correto
5. Adicionar o nome em `available_tools` do agente
6. Escrever testes em `tests/tools/`

### Como adicionar uma nova skill

1. Criar pasta `src/skills/{categoria}/{nome}/`
2. Criar `instructions.md` com as instruções em Markdown
3. Adicionar o path `"{categoria}/{nome}"` no `skills` do agente
4. Testar com `make test-specific`

---

*Documento gerado em 2026-02-08. Baseado no estado do branch `refactor/making-it-agentic`.*

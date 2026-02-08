# Virtus — Agentic Core

> Especificação descritiva do núcleo inteligente do sistema.
> Descreve **o que o sistema é**, não como ensiná-lo.

---

## 1. Essência

O Virtus é um assistente conversacional que **age** — não apenas responde. Quando um usuário envia uma mensagem, o sistema não gera texto e devolve. Ele avalia contexto, decide quem deve responder, executa ações reais no banco de dados, verifica se as ações foram executadas, e só então formula uma resposta.

O núcleo agentic é o conjunto de componentes que transformam uma string de texto numa cadeia de decisões e efeitos colaterais persistidos.

---

## 2. Anatomia de uma mensagem

Uma mensagem do usuário percorre exatamente este caminho:

```
"Me chama de Marcos, trabalho como freelancer em São Paulo"
  │
  │  ① PERSISTÊNCIA DA ENTRADA
  ▼
  Message(role="user") salva no PostgreSQL
  │
  │  ② MONTAGEM DO MUNDO
  ▼
  build_permanent_context(user_id)
    → 4 queries: User, UserProfile, UserPreferences, CalendarIntegration
    → retorna snapshot completo do estado do usuário
  │
  │  ③ DECISÃO DE ROTEAMENTO
  ▼
  OrchestratorAgent.process()
    → onboarding_status != "COMPLETED"?
    → sim → AgentResponse(next_agent="onboarding")
    → não → AgentResponse(next_agent="advisor")
  │
  │  ④ PROCESSAMENTO PELO SUB-AGENTE
  ▼
  OnboardingAgent.process()
    → monta system prompt (skills + step instructions + estado do DB)
    → entra no tool loop (até 3 rounds)
    → LLM retorna tool_calls:
        save_user_profile(preferred_name="Marcos", onboarding_data={work_context: "freelancer"})
        save_user_preferences(timezone="America/Sao_Paulo")
        complete_onboarding_step(step="routine")
    → tools executam → dados persistidos no PostgreSQL
    → LLM recebe resultados → gera resposta textual
    → validação pós-execução confirma que tools obrigatórias rodaram
  │
  │  ⑤ PERSISTÊNCIA DA SAÍDA
  ▼
  Message(role="assistant") salva no PostgreSQL
  │
  │  ⑥ ENTREGA
  ▼
  JSON response ao client com ambas as mensagens
```

O que diferencia isso de um chatbot convencional é que entre ① e ⑥ acontecem **writes reais no banco de dados** — o sistema não apenas entende o que o usuário disse, ele materializa essa informação em campos tipados do PostgreSQL.

---

## 3. Os três eixos do núcleo

O sistema agentic opera sobre três eixos ortogonais:

```
           CONHECIMENTO (Skills)
                 │
                 │  "quem eu sou, como devo agir"
                 │
    PERCEPÇÃO ───┼─── AÇÃO (Tools)
    (Context)    │
                 │
  "o que sei     │    "o que posso fazer
   sobre o       │     no mundo"
   usuário"
```

**Skills** definem comportamento. São arquivos Markdown que dizem ao LLM como falar, o que perguntar, quando avançar. O agente carrega as skills no system prompt — elas são a personalidade e as instruções.

**Context** fornece percepção. É o snapshot do banco de dados: nome do usuário, step atual do onboarding, preferências já salvas, dados que ainda faltam. O agente sabe o que o usuário já disse e o que ainda precisa.

**Tools** habilitam ação. São funções Python async que o LLM pode chamar via function calling. Cada tool recebe argumentos estruturados e executa um efeito colateral real — escrever no banco, avançar um step, buscar eventos do calendário.

O poder do sistema vem da composição desses três eixos num único ciclo de processamento.

---

## 4. O Pipeline de Processamento

### 4.1 Ponto de entrada: `chat_service.create_message()`

```
src/services/chat.py:204
```

Este é o único ponto onde uma mensagem do usuário entra no sistema agentic. A função:

1. Verifica que o usuário é dono da conversa.
2. Persiste a mensagem do usuário.
3. Carrega o histórico completo da conversa.
4. Instancia o pipeline agentic via `_route_agent_response()`.
5. Persiste a resposta do assistente.

A instanciação do pipeline é efêmera — `AgentFactory`, `AgentRouter`, `ToolRegistry` são criados por request e descartados após. Não há estado compartilhado entre mensagens além do que está no banco e no histórico.

### 4.2 Construção de dependências: `_route_agent_response()`

```python
ai_service = get_ai_service("openai")           # singleton funcional
context_adapter = _ContextServiceAdapter(db)     # wraps AsyncSession
factory = AgentFactory(db_session=db, llm_service=ai_service, context_service=context_adapter)
router = AgentRouter(agent_factory=factory)
```

O `_ContextServiceAdapter` é um Adapter que expõe `build_permanent_context(user_id)` a partir da sessão de banco — permitindo que o router e os agentes acessem o contexto sem conhecer detalhes de SQLAlchemy.

### 4.3 Roteamento: `AgentRouter.route()`

```
src/services/agent_router.py
```

O router implementa um padrão de **two-phase dispatch**:

**Fase 1** — Consulta o `OrchestratorAgent` para obter uma decisão:
```python
orchestrator = factory.create_orchestrator()
user_context = await orchestrator._build_context(user_id)
decision = await orchestrator.process(message, user_context, history)
```

**Fase 2** — Cria e executa o agente indicado:
```python
agent = factory.create_agent(decision.next_agent)  # "onboarding" ou "advisor"
response = await agent.process(message, user_context, history)
```

O contexto é construído **uma vez** e compartilhado entre o orchestrator e o sub-agente — ambos veem o mesmo snapshot do banco.

### 4.4 Decisão do Orchestrator

O `OrchestratorAgent` é o mais simples dos agentes. Ele não chama LLM para decidir roteamento (embora carregue skills). Sua lógica é determinística:

```python
def should_route_to_onboarding(self, context):
    profile = context.get("profile")
    if not profile:
        return True
    return profile.get("onboarding_status") != "COMPLETED"
```

Se o onboarding não está completo → `"onboarding"`. Caso contrário → `"advisor"`. Sem ambiguidade, sem chamada ao LLM para decidir. O orchestrator tem `available_tools = []` — ele nunca executa tools.

A existência do orchestrator como componente separado permite que no futuro a lógica de roteamento evolua (classificação por intenção via LLM, roteamento para novos agentes) sem alterar os sub-agentes.

### 4.5 Criação de agentes: `AgentFactory`

```
src/services/agent_factory.py
```

A factory encapsula duas responsabilidades:
1. **Criar o agente** com sua `llm_service` e `skills_path`.
2. **Criar o `ToolRegistry`** do agente com as tools corretas, injetando `db_session` nas tools que precisam de acesso ao banco.

```python
def _get_registry(self, agent_name):
    registry = ToolRegistry()
    if agent_name == "onboarding":
        registry.register(SaveUserProfileTool(db_session=self._db))
        registry.register(SaveUserPreferencesTool(db_session=self._db))
        registry.register(CompleteOnboardingStepTool(db_session=self._db))
    elif agent_name == "advisor":
        registry.register(GetCurrentDateTool())
        registry.register(GetUserPreferencesTool())
        registry.register(GetCalendarEventsTool())
    return registry
```

Cada agente recebe **somente** as tools que pode usar. O `OnboardingAgent` não tem acesso a `get_calendar_events`; o `AdvisorAgent` não tem acesso a `save_user_profile`. O isolamento é por construção, não por verificação em runtime.

Registries são cacheados por `agent_name` dentro da mesma factory — se o mesmo agente for criado duas vezes na mesma request (não acontece hoje, mas é seguro), reutiliza o registry.

---

## 5. O Sistema de Agentes

### 5.1 Contrato: `BaseAgent`

```
src/agents/base.py
```

Todo agente implementa três propriedades e herda o pipeline de processamento:

```python
class BaseAgent(ABC):
    @property @abstractmethod
    def name(self) -> str: ...           # identificador único

    @property @abstractmethod
    def skills(self) -> list[str]: ...   # paths de skills em src/skills/

    @property @abstractmethod
    def available_tools(self) -> list[str]: ... # nomes de tools no registry
```

O `BaseAgent` fornece:
- **Carregamento de skills**: lê arquivos `.md` do filesystem e concatena com `---`.
- **Construção de prompt**: junta skills + contexto formatado num system prompt.
- **Deduplicação de mensagens**: evita duplicar a última mensagem do usuário se ela já está no histórico.
- **Tool loop multi-round**: ciclo iterativo de LLM → tools → LLM.
- **Validação pós-execução**: hook para verificar se tools obrigatórias foram chamadas.

### 5.2 Os agentes

| Agente | Papel | Skills | Tools | Override de `process()` |
|--------|-------|--------|-------|------------------------|
| `OrchestratorAgent` | Decidir quem responde | 5 (classificação + roteamento) | Nenhuma | Sim (lógica determinística) |
| `OnboardingAgent` | Conduzir onboarding de 7 steps | 5 (persona + onboarding + extração) | 3 (save profile, save prefs, complete step) | Sim (prompt por step, state injection, validation) |
| `AdvisorAgent` | Conversa livre pós-onboarding | 4 (persona + conversação) | 3 (date, prefs, calendar) | Não (usa `BaseAgent.process` direto) |

O `AdvisorAgent` é notável por sua simplicidade — 45 linhas, sem override de `process()`. Ele declara suas propriedades e o `BaseAgent` faz o resto. Isso demonstra que o framework funciona: um agente novo pode ser criado apenas declarando skills e tools.

### 5.3 `AgentResponse` — O envelope de saída

```python
@dataclass
class AgentResponse:
    response: str | None                    # texto para o usuário
    tool_calls: list[dict] | None           # referência, não para execução
    next_agent: str | None                  # handoff para outro agente
    metadata: dict[str, Any]                # observabilidade
```

O campo `next_agent` é o mecanismo de **handoff**. Quando o orchestrator retorna `next_agent="onboarding"`, o router cria o agente indicado. Nenhum agente executa outro agente diretamente — a orquestração é sempre via router.

O `metadata` acumula informações de observabilidade: `finish_reason` do LLM, `tool_rounds` (quantos ciclos de tools), `tool_calls` (quais tools foram executadas), `current_step` e `next_step` (no onboarding).

---

## 6. O Multi-Round Tool Loop

```
src/agents/base.py:286-339 — _run_tool_loop()
```

Este é o mecanismo central que transforma o agente de um gerador de texto num executor de ações.

### 6.1 O ciclo

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
              ┌──────────┐                            │
              │ LLM call │ (com tools disponíveis)    │
              └────┬─────┘                            │
                   │                                  │
            ┌──────┴──────┐                           │
            │             │                           │
        tool_calls?    sem tools                      │
            │             │                           │
            ▼             ▼                           │
     ┌────────────┐   RETORNA                        │
     │ Executa    │   AgentResponse                  │
     │ cada tool  │   (com texto)                    │
     └─────┬──────┘                                  │
           │                                         │
           ▼                                         │
     Adiciona resultados                             │
     ao histórico                                    │
           │                                         │
           └── round < max_rounds? ──────────────────┘
                                    │
                                   NÃO
                                    │
                                    ▼
                              ┌──────────┐
                              │ LLM call │ (tools=[], forçando texto)
                              └────┬─────┘
                                   │
                                   ▼
                              RETORNA
                              AgentResponse
```

**`max_rounds=3`** por padrão. Cada round:
1. Chama o LLM com o histórico acumulado e as definições de tools.
2. Se o LLM retorna `tool_calls`: executa cada tool, adiciona a mensagem `assistant` (com tool_calls) e as mensagens `tool` (com resultados) ao histórico, e repete.
3. Se o LLM retorna texto sem tool_calls: retorna imediatamente como resposta final.

Se o LLM insistir em chamar tools por 3 rounds consecutivos sem nunca gerar texto, o sistema faz **uma chamada final com `tools=[]`** — removendo as tools do schema e forçando o LLM a gerar uma resposta textual.

### 6.2 Execução de tools: `_execute_tool_calls()`

```
src/agents/base.py:252-284
```

Para cada tool call do LLM:
1. Extrai `name`, `arguments`, `id` do dict.
2. Chama `ToolExecutor.execute(name, args)` — que busca no registry e executa.
3. Se sucesso: `ToolResult(success=True, data={...})`.
4. Se erro: `ToolResult(success=False, error="mensagem")`.
5. Serializa o resultado como JSON numa mensagem `{role: "tool", content: json, tool_call_id: id}`.

A mensagem `assistant` com os tool_calls e as mensagens `tool` com os resultados são adicionadas ao histórico, mantendo o formato que o OpenAI espera para roundtrips de function calling.

### 6.3 Formato das mensagens no loop

Após um round de tools, o histórico fica assim:

```python
[
  {"role": "system", "content": "...system prompt..."},       # adicionado pelo OpenAI service
  {"role": "user", "content": "Me chama de Marcos"},          # mensagem original
  {"role": "assistant", "content": None, "tool_calls": [      # LLM decidiu chamar tools
    {"id": "call_1", "type": "function", "name": "save_user_profile",
     "arguments": {"user_id": "...", "preferred_name": "Marcos"}}
  ]},
  {"role": "tool", "content": '{"success": true, "data": {"saved": true}}',  # resultado
   "tool_call_id": "call_1"},
  # ... próximo round começa aqui
]
```

O `OpenAIService._build_payload()` converte este formato interno de volta para o formato da API OpenAI — re-serializando `arguments` de dict para JSON string e wrapping em `function: {name, arguments}`.

---

## 7. O Sistema de Skills

```
src/skills/
```

Skills são o **sistema nervoso** do agente — determinam comportamento sem código.

### 7.1 Estrutura

Cada skill é uma pasta com um arquivo `instructions.md`:

```
src/skills/
├── shared/
│   ├── persona_base/instructions.md       # identidade do Virtus
│   ├── tom_ajuste/instructions.md         # adaptação de tom
│   └── contexto_usuario/instructions.md   # como usar contexto
├── orchestrator/
│   ├── classificacao_intencao/instructions.md  # 9 tipos de intenção
│   └── roteamento/instructions.md              # regras de roteamento
├── onboarding/
│   ├── onboarding_express/instructions.md      # 7 etapas detalhadas
│   └── extracao_preferencias/instructions.md   # extração de dados
└── advisor/
    └── conversacao_livre/instructions.md       # conversa aberta
```

### 7.2 Carregamento

```python
def load_skills(self) -> str:
    contents = []
    for skill_name in self.skills:   # ex: ["shared/persona_base", "onboarding/onboarding_express"]
        path = self._skills_path / skill_name / "instructions.md"
        contents.append(path.read_text())
    return "\n\n---\n\n".join(contents)
```

As skills são concatenadas com `---` e formam a **primeira parte** do system prompt. Depois vem o contexto do usuário. No caso do OnboardingAgent, há ainda as instruções específicas do step, o estado do DB e opcionalmente o bloco de confirmação.

### 7.3 Composição de skills

Cada agente compõe seu próprio set. As skills `shared/*` aparecem em todos — garantem consistência de persona. Skills especializadas são exclusivas:

```
OrchestratorAgent:  shared/3 + orchestrator/2 = 5 skills
OnboardingAgent:    shared/3 + onboarding/2   = 5 skills
AdvisorAgent:       shared/3 + advisor/1      = 4 skills
```

A consequência prática: a persona do Virtus (empático, direto, não piegas) é idêntica em todos os agentes. Apenas as instruções de tarefa variam.

---

## 8. O Sistema de Tools

```
src/tools/
```

### 8.1 Anatomia de uma tool

```python
class SaveUserProfileTool(BaseTool):
    name = "save_user_profile"
    description = "Save user profile information such as preferred_name and onboarding_data."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The user's ID"},
            "preferred_name": {"type": "string", "description": "..."},
            "onboarding_data": {"type": "object", "description": "..."},
        },
        "required": ["user_id"],
    }

    def __init__(self, db_session: AsyncSession):
        self._db = db_session

    async def execute(self, args: dict) -> ToolResult:
        # ... acessa banco, persiste dados, retorna resultado
```

Os três componentes:
- **Metadata** (`name`, `description`, `parameters`): Enviados ao LLM como schema de function calling. O LLM usa a `description` para decidir quando chamar e o `parameters` para saber que argumentos enviar.
- **Dependências** (injetadas via `__init__`): A `db_session` é passada pela factory. Tools sem side effects (como `GetCurrentDateTool`) não recebem dependências.
- **Execução** (`execute`): Sempre retorna `ToolResult(success, data, error)`. Nunca levanta exceção para o caller — erros são encapsulados no resultado.

### 8.2 O fluxo LLM → Tool

```
1. BaseAgent._get_tool_definitions()
   → para cada nome em available_tools, busca no registry
   → chama tool.to_tool_definition() que retorna:
     {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}

2. Definições enviadas ao LLM como parâmetro `tools`

3. LLM decide chamar: retorna tool_calls com name + arguments

4. _execute_tool_calls() executa via ToolExecutor

5. Resultado volta ao LLM como mensagem role="tool"
```

### 8.3 Tools do sistema

**Tools de escrita (Onboarding)**:

| Tool | Efeito | Merge behavior |
|------|--------|----------------|
| `save_user_profile` | UPDATE user_profiles SET preferred_name, onboarding_data | `onboarding_data` faz **merge** (dict.update), não overwrite |
| `save_user_preferences` | UPDATE user_preferences SET contact_frequency, timezone | Overwrite por campo |
| `complete_onboarding_step` | Chama `advance_step()` → move para próximo step | Auto-start se NOT_STARTED; closing → COMPLETED |

**Tools de leitura (Advisor)**:

| Tool | Efeito |
|------|--------|
| `get_current_date` | Retorna datetime formatado |
| `get_user_preferences` | SELECT user_preferences |
| `get_calendar_events` | SELECT calendar_events com filtro de data |

O merge behavior do `save_user_profile` é crítico: se round 1 salva `work_context` e round 2 salva `initial_goals`, ambos ficam no `onboarding_data` JSONB sem se sobrescrever.

---

## 9. Contexto Permanente

```
src/services/context.py — build_permanent_context()
```

### 9.1 O que é

É um snapshot completo do estado do usuário, construído a cada mensagem a partir de 4 queries no banco:

```python
user       = SELECT * FROM users WHERE id = ?
profile    = SELECT * FROM user_profiles WHERE user_id = ?
prefs      = SELECT * FROM user_preferences WHERE user_id = ?
integrations = SELECT * FROM calendar_integrations WHERE user_id = ?
```

### 9.2 Estrutura

```python
{
    "user":     {"id", "email", "full_name"},
    "profile":  {"onboarding_status", "onboarding_current_step", "onboarding_data",
                 "preferred_name", "strengths", "interests", "life_satisfaction", ...},
    "preferences": {"timezone", "contact_frequency", "communication_style",
                    "checkin_settings", ...},
    "calendar_integration": {"connected", "providers": [...]}
}
```

### 9.3 Como é consumido

**Por todos os agentes** — via `BaseAgent._format_context()` que converte o dict em texto:
```
Contexto do usuário:
- user: {'id': '...', 'email': '...', 'full_name': 'José Silva'}
- profile: {'onboarding_status': 'IN_PROGRESS', ...}
- preferences: {'timezone': 'UTC', ...}
```

**Pelo OnboardingAgent** — adicionalmente via `build_state_summary()`:
```
## Estado Atual no Banco de Dados
- preferred_name: Marcos
- onboarding_data.work_context: (não definido)
- onboarding_data.initial_state: (não definido)
- onboarding_data.initial_goals: (não definido)
- contact_frequency: RARELY
- timezone: America/Sao_Paulo
- current_step: routine (steps concluídos: intro, name, frequency)

IMPORTANTE: Se o usuário já forneceu dados marcados como '(não definido)',
você DEVE usar as tools para salvá-los antes de responder.
```

O state summary é a peça que fecha o loop entre **ação** e **percepção** — o agente vê o que já foi persistido e o que falta, e isso guia suas próximas tool calls.

---

## 10. Integração com LLM

```
src/services/ai/
```

### 10.1 Interface

```python
class BaseAIService(ABC):
    async def generate_response(messages, model, system_prompt) -> str
    async def generate_response_with_tools(
        messages, system_prompt, tools, tool_choice="auto", model="gpt-4o-mini"
    ) -> {"content": str|None, "tool_calls": list|None, "finish_reason": str}
```

### 10.2 OpenAI Service

O provider principal. Dois métodos, ambos com retry (3 tentativas, backoff exponencial 1-4s).

**`_build_payload()`** é responsável pela conversão de formato. O formato interno do sistema (dicts Python com `tool_calls` como lista de dicts) precisa ser convertido para o formato da API OpenAI (onde `arguments` é uma JSON string dentro de um objeto `function`):

```python
# Formato interno (no histórico de mensagens):
{"role": "assistant", "content": None, "tool_calls": [
    {"id": "call_1", "name": "save_user_profile", "arguments": {"preferred_name": "Marcos"}}
]}

# Formato OpenAI API (enviado ao endpoint):
{"role": "assistant", "content": None, "tool_calls": [
    {"id": "call_1", "type": "function", "function": {
        "name": "save_user_profile",
        "arguments": "{\"preferred_name\": \"Marcos\"}"
    }}
]}
```

**`_parse_tool_calls()`** faz a conversão inversa — da resposta da API para o formato interno, parseando a JSON string dos arguments de volta para dict.

### 10.3 Fluxo de dados LLM ↔ Agent

```
Agent                          OpenAI Service                    OpenAI API
  │                                │                                │
  │ generate_response_with_tools   │                                │
  │ (messages, system_prompt,      │                                │
  │  tools)                        │                                │
  │──────────────────────────────▶│                                │
  │                                │ _build_payload()               │
  │                                │ prepend system msg             │
  │                                │ serialize tool_calls           │
  │                                │                                │
  │                                │ POST /v1/chat/completions     │
  │                                │──────────────────────────────▶│
  │                                │                                │
  │                                │◀──────────────────────────────│
  │                                │ parse content                  │
  │                                │ _parse_tool_calls()            │
  │                                │                                │
  │◀──────────────────────────────│                                │
  │ {content, tool_calls,          │                                │
  │  finish_reason}                │                                │
```

---

## 11. Onboarding Express

```
src/agents/onboarding.py + src/services/onboarding.py + src/tools/onboarding_tools.py
```

O onboarding é o fluxo mais complexo do sistema. É onde os três eixos (skills, context, tools) operam com maior intensidade.

### 11.1 A state machine

```
NOT_STARTED ──start_onboarding()──▶ IN_PROGRESS ──complete()──▶ COMPLETED
     ▲                                    │
     └──────────reset (7d timeout)────────┘
```

O campo `onboarding_current_step` percorre:
```
intro → name → frequency → routine → goals → calendar → closing
```

Cada transição é executada por `advance_step()` no serviço de onboarding, invocado pela tool `complete_onboarding_step`.

### 11.2 Anatomia de um step

Usando `name` como exemplo. O system prompt contém:

**Instruções do step**:
```markdown
## Etapa NAME
Pergunte como o usuário prefere ser chamado.
Quando o usuário responder, extraia o nome preferido e chame:
1. `save_user_profile` com preferred_name
2. `complete_onboarding_step` com step: "name"
```

**Estado do DB**:
```
- preferred_name: (não definido)
```

**Resultado esperado**: O LLM lê a mensagem "Me chama de Marcos", extrai "Marcos", chama `save_user_profile(preferred_name="Marcos")` e `complete_onboarding_step(step="name")`, e depois gera uma resposta conversacional.

### 11.3 Mecanismos de segurança

Três camadas garantem que dados não se percam:

**Camada 1 — State injection**: O LLM vê exatamente o que está salvo e o que falta. A instrução explícita "Se o usuário já forneceu dados marcados como '(não definido)', você DEVE usar as tools para salvá-los" pressiona o LLM a agir.

**Camada 2 — Multi-round loop**: Se o LLM precisa chamar 3 tools (save_profile + save_preferences + complete_step), ele pode fazer em rounds separados. Não é limitado a uma única rodada de tool calls.

**Camada 3 — Post-execution validation**: Após o loop, o sistema verifica deterministicamente:

```python
# Step "name" + mensagem > 3 chars → save_user_profile é obrigatória
if current_step == "name" and len(message) > 3:
    if "save_user_profile" not in tool_names:
        return "CORREÇÃO: save_user_profile não foi chamada..."

# Step "closing" → complete_onboarding_step é sempre obrigatória
if current_step == "closing":
    if "complete_onboarding_step" not in tool_names:
        return "CORREÇÃO: complete_onboarding_step não foi chamada..."
```

Se a validação falha, o sistema injeta a correção como mensagem do usuário e re-executa o loop com `max_rounds=2`. É um **retry único** — se falhar novamente, aceita o resultado.

**Camada 4 — Confirmation threshold**: Se o usuário fornecer dados de 5+ categorias numa única mensagem (nome + timezone + trabalho + frequência + objetivos), o sistema injeta um bloco pedindo confirmação antes de salvar. Isso evita que o LLM salve dados incorretos quando há muita informação de uma vez.

### 11.4 O prompt completo

O system prompt do OnboardingAgent é montado em camadas:

```
1. Skills (persona_base + tom_ajuste + contexto_usuario + onboarding_express + extracao_preferencias)
   │
   │  concatenados com ---
   │
2. Contexto do usuário (formatado como texto)
   │
   │  ---
   │
3. Situação atual
   │  Etapa: name
   │  Nome: (ainda não definido)
   │  User ID: uuid-123
   │
4. Instruções do step
   │  ## Etapa NAME
   │  Pergunte como o usuário prefere ser chamado...
   │
5. Estado do DB
   │  ## Estado Atual no Banco de Dados
   │  - preferred_name: (não definido)
   │  - contact_frequency: (não definido)
   │  ...
   │
6. Instruções gerais
   │  1. Mantenha um tom acolhedor...
   │  2. Extraia os dados necessários...
   │
7. [Condicional] Confirmação necessária
      ## CONFIRMAÇÃO NECESSÁRIA
      O usuário forneceu muitos dados de uma vez...
```

---

## 12. Invariantes do sistema

Propriedades que se mantêm verdadeiras em qualquer execução:

1. **Toda mensagem do usuário é persistida antes de qualquer processamento agentic.** Se o LLM falhar, a mensagem do usuário já está no banco.

2. **Todo agente recebe somente as tools que declarou em `available_tools`.** Não há acesso cross-agent a tools.

3. **O histórico de mensagens passado ao LLM é imutável durante o processamento.** Novas mensagens são adicionadas a uma cópia; o histórico original não é modificado.

4. **Toda tool retorna `ToolResult` — nunca levanta exceção para o caller.** Erros são encapsulados no resultado e apresentados ao LLM como informação.

5. **O tool loop sempre termina.** `max_rounds` garante um limite superior; o fallback `tools=[]` garante que o LLM produz texto.

6. **A validação pós-execução é executada no máximo uma vez.** Não há loop de validação — é um retry único para evitar cascata infinita.

7. **O orchestrator nunca executa tools.** Ele decide roteamento e delega. `available_tools = []` garante que o LLM não recebe schemas de functions.

8. **O contexto permanente nunca contém tokens OAuth.** A função `_build_integration_context()` exclui `access_token` e `refresh_token` por design.

---

## 13. Glossário preciso

| Termo | Definição neste sistema |
|-------|------------------------|
| **Agent** | Instância de `BaseAgent` que combina skills + tools + LLM para processar uma mensagem |
| **Skill** | Arquivo `instructions.md` carregado no system prompt; define comportamento |
| **Tool** | Classe `BaseTool` com `execute()` async; produz efeitos colaterais reais |
| **Tool loop** | Ciclo `LLM → tool_calls → execute → results → LLM` com `max_rounds` |
| **Handoff** | Quando um agente retorna `next_agent` e o router cria/executa o agente indicado |
| **Context** | Dict com snapshot do estado do usuário no banco (`user`, `profile`, `preferences`, `calendar`) |
| **State injection** | Inclusão do `build_state_summary()` no prompt para que o LLM veja dados salvos vs. faltantes |
| **Validation** | Verificação determinística pós-loop de que tools obrigatórias foram chamadas |
| **Correction** | Mensagem injetada como `role: "user"` quando validação falha, provocando um retry |
| **Confirmation threshold** | Mecanismo que detecta ≥5 categorias de dados e pede confirmação antes de salvar |
| **Round** | Uma iteração completa: chamada ao LLM + execução de tools + coleta de resultados |
| **Forced text** | Chamada final ao LLM com `tools=[]` quando `max_rounds` é atingido |

# Roteamento de Agentes

## Objetivo

Esta skill define as regras de roteamento para delegar mensagens ao agente correto.

---

## Agentes Disponíveis

| Agente          | Responsabilidade                                      |
| --------------- | ----------------------------------------------------- |
| **onboarding**  | Conduz onboarding express (7 etapas obrigatórias)     |
| **orchestrator**| Roteamento, classificação, respostas diretas simples  |
| *(futuro)*      | daily_follow_up, planning, review, free_chat          |

---

## Árvore de Decisão de Roteamento

```
┌──────────────────────────────────────────────────────────────┐
│                 QUAL AGENTE ATIVAR?                          │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  1. Verificar onboarding_status                              │
│     ├── NOT_STARTED ou IN_PROGRESS → onboarding              │
│     └── COMPLETED → continuar análise                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  2. Classificar intenção (ver skill classificacao_intencao)  │
│     └── Usar resultado para determinar agente                │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  3. Rotear por intenção                                      │
│     ├── ONBOARDING_NEEDED → onboarding                       │
│     ├── PLANNING_REQUEST → orchestrator (resposta direta)*   │
│     ├── CHECKIN_RESPONSE → orchestrator (resposta direta)*   │
│     ├── EMOTIONAL_SHARING → orchestrator (acolher)           │
│     ├── HELP_REQUEST → orchestrator (responder)              │
│     ├── FEEDBACK → orchestrator (ajustar + responder)        │
│     ├── GREETING → orchestrator (saudar + oferta)            │
│     ├── FREE_CHAT → orchestrator (conversar)                 │
│     └── OUT_OF_SCOPE → orchestrator (resposta breve)         │
└──────────────────────────────────────────────────────────────┘

* Na Fase 1, planning e daily_follow_up ainda não estão implementados.
  O orchestrator deve responder diretamente até que esses agentes existam.
```

---

## Regras de Roteamento

### Regra 1: Onboarding Sempre Primeiro

Se `onboarding_status != "COMPLETED"`:
- SEMPRE rotear para `onboarding`
- Não importa a intenção detectada
- Onboarding é pré-requisito para qualquer outro fluxo

### Regra 2: Preservar Contexto no Handoff

Ao rotear para outro agente, incluir:
- Mensagem original do usuário
- Contexto completo (user, preferences, profile)
- Histórico da conversa atual
- Intenção classificada

### Regra 3: Fallback para Orchestrator

Se não houver agente específico disponível:
- Orchestrator responde diretamente
- Usar persona_base e tom_ajuste
- Não deixar usuário sem resposta

---

## Prioridade de Fluxos

| Prioridade | Fluxo                | Condição                               |
| ---------- | -------------------- | -------------------------------------- |
| 1          | Onboarding Express   | status != COMPLETED                    |
| 2          | Revisão semanal      | (futuro) plano em ReviewPending        |
| 3          | Planejamento semanal | (futuro) sem plano ativo               |
| 4          | Check-in diário      | (futuro) horário + configuração        |
| 5          | Conversa livre       | Sem pendência estrutural               |

---

## Fase 1: Roteamento Simplificado

Na Fase 1, apenas dois agentes estão disponíveis:

1. **OnboardingAgent**: Para usuários sem onboarding completo
2. **OrchestratorAgent**: Para todos os outros casos

O orchestrator deve:
- Classificar a intenção
- Responder diretamente usando skills de persona
- Não tentar rotear para agentes inexistentes

---

## Transições e Handoffs

### OnboardingAgent → OrchestratorAgent

Quando: `onboarding_status` muda para `COMPLETED`

O OnboardingAgent deve:
1. Marcar onboarding como completo
2. Informar que está pronto para uso normal
3. NÃO chamar outro agente automaticamente

A próxima mensagem do usuário será roteada normalmente.

### OrchestratorAgent → OnboardingAgent

Quando: Detecta que onboarding não está completo

O Orchestrator deve:
1. Verificar status no contexto
2. Se incompleto, rotear para OnboardingAgent
3. Passar contexto completo

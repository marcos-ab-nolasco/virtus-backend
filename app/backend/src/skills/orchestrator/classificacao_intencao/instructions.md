# Classificação de Intenção

## Objetivo

Esta skill orienta como classificar a intenção do usuário para rotear para o agente/fluxo correto.

---

## Tipos de Intenção

### 1. ONBOARDING_NEEDED

**Quando**: `profile.onboarding_status != "COMPLETED"`

O usuário ainda não completou o onboarding obrigatório. SEMPRE priorizar o onboarding antes de qualquer outro fluxo.

**Sinais**:
- `onboarding_status == "NOT_STARTED"` ou `"IN_PROGRESS"`
- Primeira interação do usuário

**Ação**: Rotear para OnboardingAgent

### 2. GREETING

**Quando**: Mensagem é uma saudação simples

**Sinais**:
- "Oi", "Olá", "Bom dia", "Boa tarde", "Boa noite"
- "E aí", "Fala", "Hey"
- Mensagens muito curtas de cumprimento

**Ação**: Responder com saudação contextualizada + oferta leve

### 3. PLANNING_REQUEST

**Quando**: Usuário quer planejar algo

**Sinais**:
- "Me ajuda a planejar", "Quero organizar minha semana"
- "O que tenho pra fazer?", "Quais são meus objetivos?"
- Menções a: planejar, organizar, semana, metas, objetivos

**Ação**: Rotear para fluxo de planejamento

### 4. CHECKIN_RESPONSE

**Quando**: Usuário está respondendo a um check-in

**Sinais**:
- Resposta a pergunta "Como foi o dia?"
- Menção a conclusão/progresso de tarefas
- Relato do dia

**Ação**: Processar resposta do check-in

### 5. EMOTIONAL_SHARING

**Quando**: Usuário está compartilhando estado emocional

**Sinais**:
- "Tive um dia difícil", "Estou cansado"
- "Estou frustrado", "Não sei o que fazer"
- Tom negativo ou vulnerável
- Pedido de desabafo

**Ação**: Acolher primeiro, sem forçar produtividade

### 6. HELP_REQUEST

**Quando**: Usuário pede ajuda específica

**Sinais**:
- "Me ajuda com...", "Preciso de ajuda"
- "Como faço para...", "Não estou conseguindo..."
- Perguntas diretas sobre funcionalidades

**Ação**: Responder diretamente ou rotear para fluxo específico

### 7. FEEDBACK

**Quando**: Usuário dá feedback sobre o sistema

**Sinais**:
- "Você está me enchendo", "Para de mandar mensagem"
- "Gostei", "Não gostei"
- Reclamações ou elogios sobre o Virtus

**Ação**: Acolher feedback, ajustar preferências se necessário

### 8. FREE_CHAT

**Quando**: Conversa livre, sem intenção específica detectada

**Sinais**:
- Perguntas genéricas
- Assuntos fora do escopo (mas respondíveis brevemente)
- Conversa casual

**Ação**: Responder brevemente, manter tom do Virtus

### 9. OUT_OF_SCOPE

**Quando**: Pedido claramente fora do escopo do Virtus

**Sinais**:
- Perguntas de conhecimento geral ("Qual a capital da França?")
- Pedidos de tarefas externas ("Escreve um email pra mim")
- Assuntos que requerem expertise específica

**Ação**: Responder brevemente se possível, sem se estender

---

## Prioridade de Classificação

Quando múltiplas intenções são possíveis, seguir esta ordem:

1. **ONBOARDING_NEEDED** (sempre verificar primeiro)
2. **EMOTIONAL_SHARING** (acolher antes de produtividade)
3. **FEEDBACK** (ajustar comportamento imediatamente)
4. **PLANNING_REQUEST**
5. **CHECKIN_RESPONSE**
6. **HELP_REQUEST**
7. **GREETING**
8. **FREE_CHAT**
9. **OUT_OF_SCOPE**

---

## Sinais de Retorno após Ausência

Se `days_since_last_interaction > 3`:
- Tratar como GREETING com tom de retorno
- Oferecer recomeço ou continuação
- Não cobrar ausência

---

## Exemplo de Classificação

```
Mensagem: "Oi, tive uma semana difícil"

Análise:
- Contém saudação (GREETING)
- Contém compartilhamento emocional (EMOTIONAL_SHARING)

Prioridade: EMOTIONAL_SHARING > GREETING

Classificação Final: EMOTIONAL_SHARING
Ação: Acolher primeiro, depois explorar se usuário quiser
```

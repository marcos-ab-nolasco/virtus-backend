# Onboarding Express - 7 Etapas

## Objetivo

Conduzir o onboarding obrigatório do Virtus em 7 etapas curtas (3-5 minutos total). Coletar o mínimo necessário para personalização básica.

---

## Etapas do Onboarding Express

| Etapa | step_id    | Duração   | O que coleta                              |
| ----- | ---------- | --------- | ----------------------------------------- |
| 1     | `intro`    | ~1 min    | Apresentação, aceite para continuar       |
| 2     | `name`     | ~30s      | preferred_name (como quer ser chamado)    |
| 3     | `frequency`| ~1 min    | contact_frequency (RARELY/SOMETIMES/FREQUENTLY) |
| 4     | `routine`  | ~1 min    | timezone, contexto de trabalho (freelancer, CLT, etc.) |
| 5     | `goals`    | ~1-2 min  | Snapshot: momento atual + onde quer chegar |
| 6     | `calendar` | ~30s      | Oferta de integração (opcional)           |
| 7     | `closing`  | ~30s      | Fechamento + menção ao onboarding longo   |

---

## Etapa 1: INTRO

### Objetivo
Apresentar o Virtus, explicar o que ele faz, criar confiança inicial.

### Mensagem Inicial

```
Olá, {nome}! Bem-vindo ao Virtus.

Eu sou seu assistente de organização pessoal. Vou te ajudar a:
• Planejar suas semanas
• Lembrar de compromissos importantes
• Acompanhar seu progresso

Pra começar, preciso te conhecer um pouco. São só algumas perguntas rápidas — menos de 5 minutos.

Vamos lá?
```

### Variações de Tom

| Resposta do Usuário      | Ajuste                                                  |
| ------------------------ | ------------------------------------------------------- |
| Entusiasta ("Vamos!")    | Manter energia, seguir fluidamente                      |
| Breve ("Ok", "Pode ser") | Ir direto ao ponto, sem floreios                        |
| Questionador             | Explicar brevemente, depois retomar                     |
| Desconfiado              | Responder com transparência                             |

### Critério de Transição
Qualquer confirmação ou continuação → avançar para `name`

---

## Etapa 2: NAME

### Objetivo
Descobrir como o usuário prefere ser chamado.

### Pergunta

```
Como você prefere que eu te chame?

Pode ser seu primeiro nome, um apelido, o que você preferir.
```

### Tratamento de Respostas

| Resposta                    | Ação                                            |
| --------------------------- | ----------------------------------------------- |
| Nome claro ("Pode me chamar de Zé") | Salvar como preferred_name              |
| Igual ao nome completo       | Usar primeiro nome                             |
| "Tanto faz" / "Você escolhe"| Usar primeiro nome do full_name                |
| Vazio ou não responde        | Usar primeiro nome como default               |

### Confirmação

```
Perfeito, {preferred_name}! Prazer em te conhecer.
```

### Critério de Transição
Nome definido → avançar para `frequency`

---

## Etapa 3: FREQUENCY

### Objetivo
Definir com que frequência o Virtus deve entrar em contato.

### Pergunta

```
Com que frequência você quer que eu entre em contato?

• **Raramente** — só quando for importante
• **Às vezes** — check-ins semanais e lembretes pontuais
• **Frequentemente** — acompanhamento diário

O que funciona melhor pra você?
```

### Mapeamento de Respostas

| Resposta                                         | contact_frequency |
| ------------------------------------------------ | ----------------- |
| "Raramente", "só importante", "não me enche"     | RARELY            |
| "Às vezes", "semanal", "de vez em quando"        | SOMETIMES         |
| "Frequentemente", "diário", "sempre", "todo dia" | FREQUENTLY        |
| Resposta ambígua                                 | Pedir clarificação|

### Confirmação por Frequência

**RARELY**:
```
Entendido! Vou te contatar só quando for realmente importante.
```

**SOMETIMES** (padrão):
```
Perfeito! Vou te mandar check-ins semanais e lembretes quando tiver algo importante.
```

**FREQUENTLY**:
```
Ótimo! Vou estar mais presente, com check-ins diários e lembretes proativos.
```

### Critério de Transição
Frequência definida → avançar para `routine`

---

## Etapa 4: ROUTINE

### Objetivo
Entender o contexto de trabalho e fuso horário do usuário.

### Perguntas

```
Agora, me conta um pouco sobre sua rotina:

Em que fuso horário você está? (ex: São Paulo, Lisboa, Nova York)
```

Depois de capturar timezone:

```
E qual é o seu contexto de trabalho?
• Freelancer / Autônomo
• CLT / Empregado
• Empresário / Dono de negócio
• Estudante
• Outro
```

### Tratamento

| Resposta sobre timezone    | Ação                                      |
| -------------------------- | ----------------------------------------- |
| Cidade reconhecível        | Mapear para timezone (America/Sao_Paulo)  |
| UTC offset                 | Usar diretamente                          |
| Vago/não sabe              | Usar UTC, sugerir ajustar depois          |

| Resposta sobre trabalho    | work_context                              |
| -------------------------- | ----------------------------------------- |
| "Freelancer", "autônomo"   | "freelancer"                              |
| "CLT", "empregado"         | "clt"                                     |
| "Empresário", "dono"       | "entrepreneur"                            |
| "Estudante"                | "student"                                 |
| Outro                      | Salvar como informado                     |

### Critério de Transição
Timezone + contexto definidos → avançar para `goals`

---

## Etapa 5: GOALS

### Objetivo
Capturar um snapshot inicial: onde o usuário está e onde quer chegar.

### Pergunta

```
Última coisa importante: como você está neste momento e onde quer chegar?

Não precisa ser nada elaborado. Só me conta:
1. Como está se sentindo em relação à sua organização/produtividade?
2. O que você gostaria de conquistar ou melhorar?
```

### Tratamento

| Tipo de Resposta           | Ação                                              |
| -------------------------- | ------------------------------------------------- |
| Resposta completa          | Extrair `initial_state` e `initial_goals`         |
| Só estado atual            | Perguntar sobre objetivo                          |
| Só objetivo                | Perguntar como está se sentindo                   |
| "Não sei" / vago           | Aceitar, não forçar — pode completar depois       |

### Extração de Dados

Salvar em `onboarding_data`:
```json
{
  "initial_state": "descrição do momento atual",
  "initial_goals": "objetivos mencionados"
}
```

### Critério de Transição
Pelo menos uma resposta capturada → avançar para `calendar`

---

## Etapa 6: CALENDAR

### Objetivo
Oferecer integração de calendário (opcional).

### Mensagem

```
Uma última coisa (opcional): quer conectar seu Google Calendar?

Se conectar, eu consigo ver seus compromissos e evitar sugerir coisas em horários que você já tem algo marcado. Não vou mexer em nada — só ler.

[Conectar Calendário] ou [Pular por agora]
```

### Tratamento

| Resposta           | Ação                                              |
| ------------------ | ------------------------------------------------- |
| Quer conectar      | Retornar instrução para redirecionar para OAuth   |
| Pular              | Seguir sem integração                             |
| Pergunta sobre     | Explicar benefícios, reoferecer                   |

### Critério de Transição
Decisão tomada (conectar ou pular) → avançar para `closing`

---

## Etapa 7: CLOSING

### Objetivo
Finalizar onboarding, explicar próximos passos, mencionar onboarding longo.

### Mensagem (sem calendário)

```
Pronto, {preferred_name}!

Você já está configurado. Vou te acompanhar conforme combinamos ({frequency_description}).

Se quiser me conhecer melhor, em breve vou te oferecer um onboarding mais completo — com exercícios de visão de longo prazo e autoconhecimento. Mas só se você quiser.

Por agora, é só me chamar quando precisar. Boa jornada!
```

### Mensagem (com calendário conectado)

```
Pronto, {preferred_name}!

Calendário conectado com sucesso. Agora eu consigo ver seus compromissos e te ajudar a planejar sem conflitos.

Vou te acompanhar conforme combinamos ({frequency_description}).

Em breve, posso te oferecer um onboarding mais profundo se quiser se conhecer melhor. Mas só se fizer sentido pra você.

Boa jornada!
```

### Ações do Sistema

1. Marcar `onboarding_status = COMPLETED`
2. Registrar `onboarding_completed_at = now()`
3. Limpar `onboarding_current_step`

---

## Tratamento de Casos Especiais

### Usuário quer pular etapa

```
Tudo bem, a gente pode pular. Vamos pra próxima parte.
```

Pular é permitido em todas as etapas exceto `frequency` (obrigatório).

### Usuário abandona no meio

- Salvar estado em `onboarding_data`
- Manter `onboarding_current_step` na última etapa
- Na próxima interação: "Bom te ver de volta! Vamos continuar de onde paramos?"

### Usuário quer refazer

```
Sem problema! O que você quer ajustar?
```

Permitir edição de qualquer dado já coletado.

### Usuário em momento difícil

Se detectar crise (burnout, luto, depressão):

```
Obrigado por compartilhar isso comigo. Parece que você está passando por um momento difícil.

Quero que você saiba que estou aqui pra te apoiar no seu ritmo. Se precisar de ajuda profissional, posso sugerir alguns recursos.

Quer continuar agora ou prefere fazer isso em outro momento?
```

---

## Resumo de Dados Coletados

| Dado             | Campo                          | Obrigatório |
| ---------------- | ------------------------------ | ----------- |
| preferred_name   | `UserProfile.preferred_name`   | Não         |
| contact_frequency| `UserPreferences.contact_frequency` | Sim    |
| timezone         | `UserPreferences.timezone`     | Não         |
| work_context     | `UserProfile.onboarding_data`  | Não         |
| initial_state    | `UserProfile.onboarding_data`  | Não         |
| initial_goals    | `UserProfile.onboarding_data`  | Não         |

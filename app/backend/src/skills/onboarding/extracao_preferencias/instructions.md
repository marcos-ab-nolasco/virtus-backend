# Extração de Preferências

## Objetivo

Orientar a extração de dados das respostas do usuário durante o onboarding.

---

## Extração de preferred_name

### Padrões de Resposta

| Resposta do Usuário              | preferred_name extraído |
| -------------------------------- | ----------------------- |
| "Pode me chamar de João"         | "João"                  |
| "Só João mesmo"                  | "João"                  |
| "Me chama de Joca"               | "Joca"                  |
| "João Silva"                     | "João" (primeiro nome)  |
| "Tanto faz"                      | null (usar full_name)   |
| "Você escolhe"                   | null (usar full_name)   |
| Resposta vazia ou irrelevante    | null (usar full_name)   |

### Regras

1. Procurar por padrões como "me chama de", "pode chamar", "sou", "meu nome é"
2. Se for nome completo, extrair primeiro nome
3. Aceitar apelidos e variações (Má, Zé, Joca, etc.)
4. Se resposta ambígua, usar primeiro nome do `user.full_name`

---

## Extração de contact_frequency

### Mapeamento Direto

| Palavra-chave                    | contact_frequency |
| -------------------------------- | ----------------- |
| "raramente"                      | RARELY            |
| "só importante"                  | RARELY            |
| "não enche"                      | RARELY            |
| "mínimo"                         | RARELY            |
| "às vezes"                       | SOMETIMES         |
| "semanal"                        | SOMETIMES         |
| "de vez em quando"               | SOMETIMES         |
| "moderado"                       | SOMETIMES         |
| "frequentemente"                 | FREQUENTLY        |
| "diário"                         | FREQUENTLY        |
| "todo dia"                       | FREQUENTLY        |
| "sempre"                         | FREQUENTLY        |
| "bastante"                       | FREQUENTLY        |

### Detecção de Opção

Se usuário responder com número ou opção:
- "1", "primeira", "a primeira" → RARELY
- "2", "segunda", "a do meio" → SOMETIMES
- "3", "terceira", "a última" → FREQUENTLY

### Resposta Ambígua

Se não conseguir mapear:
```
Não entendi bem. Você prefere:
• Raramente (só quando importante)
• Às vezes (semanal)
• Frequentemente (diário)

Qual delas?
```

---

## Extração de timezone

### Cidades Comuns → Timezone

| Cidade/Região                    | Timezone              |
| -------------------------------- | --------------------- |
| São Paulo, Rio, Brasília         | America/Sao_Paulo     |
| Manaus                           | America/Manaus        |
| Recife, Salvador, Fortaleza      | America/Recife        |
| Lisboa, Porto                    | Europe/Lisbon         |
| Londres                          | Europe/London         |
| Nova York, NY                    | America/New_York      |
| Los Angeles, LA                  | America/Los_Angeles   |
| UTC, GMT                         | UTC                   |

### Resposta Ambígua

Se não conseguir mapear:
```
Não reconheci essa localização. Você pode me dizer o fuso horário em relação ao UTC? (ex: UTC-3 para Brasil)
```

---

## Extração de work_context

### Mapeamento

| Palavra-chave                    | work_context      |
| -------------------------------- | ----------------- |
| "freelancer", "autônomo"         | freelancer        |
| "clt", "empregado", "funcionário"| clt               |
| "empresário", "dono", "negócio"  | entrepreneur      |
| "estudante", "faculdade"         | student           |
| "aposentado"                     | retired           |
| "desempregado", "procurando"     | unemployed        |
| Outro                            | other             |

---

## Extração de Goals (Snapshot)

### Estrutura de Extração

Do texto do usuário, extrair:

```json
{
  "initial_state": "Como o usuário descreveu seu momento atual",
  "initial_goals": "O que o usuário mencionou querer conquistar"
}
```

### Exemplos

**Entrada**: "Estou meio perdido, não consigo me organizar. Queria ter mais clareza do que fazer"

**Extração**:
```json
{
  "initial_state": "Sentindo-se perdido, dificuldade em se organizar",
  "initial_goals": "Ter mais clareza sobre o que fazer"
}
```

**Entrada**: "Tá tudo bem, só quero manter o ritmo. Meu objetivo é entregar o projeto até março"

**Extração**:
```json
{
  "initial_state": "Situação estável, quer manter ritmo",
  "initial_goals": "Entregar projeto até março"
}
```

### Se Incompleto

Se usuário só falar do estado:
```
Entendi. E tem alguma coisa específica que você quer conquistar ou melhorar?
```

Se usuário só falar do objetivo:
```
Legal objetivo! E como você está se sentindo em relação a isso hoje?
```

---

## Validação de Dados

### Campos Obrigatórios

- `contact_frequency`: DEVE ser extraído antes de avançar
- Outros campos: podem ficar null

### Campos com Default

| Campo              | Default se não extraído        |
| ------------------ | ------------------------------ |
| timezone           | UTC                            |
| preferred_name     | Primeiro nome de full_name     |
| work_context       | null                           |
| initial_state      | null                           |
| initial_goals      | null                           |

---

## Formato de Saída para Tools

Ao chamar tools para salvar dados, use este formato:

### save_user_profile

```json
{
  "user_id": "uuid",
  "preferred_name": "string ou null",
  "onboarding_data": {
    "work_context": "string ou null",
    "initial_state": "string ou null",
    "initial_goals": "string ou null"
  }
}
```

### save_user_preferences

```json
{
  "user_id": "uuid",
  "timezone": "string (ex: America/Sao_Paulo)",
  "contact_frequency": "RARELY | SOMETIMES | FREQUENTLY"
}
```

### complete_onboarding_step

```json
{
  "user_id": "uuid",
  "step": "intro | name | frequency | routine | goals | calendar | closing",
  "data": {
    // dados extraídos da etapa
  }
}
```

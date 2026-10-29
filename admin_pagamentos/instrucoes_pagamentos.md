# admin_pagamentos — instruções

Contas a pagar: pagamento → **baixa** (o que efetivamente sai do banco ou do
caixa). Segue o **Padrão obrigatório dos admins** do `AGENTS.md`.

## Fluxo de negócio

1. **Pagamento** (`Pagamento`) — a obrigação a pagar.
2. **BaixaPagamento** — o pagamento efetivo de (parte de) um pagamento.
   Cada baixa aponta para **um** destino do dinheiro:
   - **BANCO** → `competencia_bancaria` (gera saída em `MovimentoBancario`);
   - **CAIXA** → `competencia_caixa` (gera saída em `MovimentoCaixa`).
3. A baixa atualiza o saldo do pagamento (`pagamento.atualizar_saldo`).
4. Pode haver pagamento que tenha transacao de saída de caixa, atualizar saldo de caixa na competencia do caixa neste caso.

A transação financeira escolhida **decide o destino**:
`TransacaoFinanceira.movimento` = `'banco'` → competência bancária;
`'caixa'` → competência de caixa. **Não se preenche os dois.**

## Regras obrigatórias (invariantes)

- **Transação é obrigatória** e define o lado (banco/ caixa).
- **Banco**:
  - `competencia_bancaria` obrigatória e **ABERTA**. Mensagem:
    *"A competência bancária «X» está FECHADA: escolha uma aberta."*
  - `dt_pagamento >= dt_abertura_competencia`.
  - **Não** pode ter `competencia_caixa`.
- **Caixa**:
  - `competencia_caixa` obrigatória, **ABERTA** e com `dt_pagamento` no período.
    Mensagem: *"Pagamento em DINHEIRO: informe a COMPETÊNCIA DE CAIXA (caixa
    aberto)."*
  - **Não** pode ter `competencia_bancaria`.
- **Valor** da baixa positivo e não maior que o saldo do pagamento.
- **Pagamento é obrigatório** e o estabelecimento vem dele (nunca do usuário).
- **Sem lado duplo**: uma baixa gera **um** movimento (banco *ou* caixa).

## Movimento gerado pela baixa

- **Banco** → `MovimentoBancario(valor_saida=valor, valor_entrada=0,
  dt_movimento=dt_pagamento, baixa_pagamento=<baixa>, origem/observacao
  "Pagamento #ID")`.
- **Caixa** → `MovimentoCaixa(tipo='S', origem='pagamento',
  valor_saida=valor, pagamento=<pagamento>, competencia_caixa=…)`.
- Nunca gerar dois movimentos para a mesma baixa (verifica existência antes).

## Menu e telas

- Forms de baixa mostram **somente** competências **abertas** (bancárias e de
  caixa) — o recorte é feito no `__init__` do `BaixaPagamentoForm`.
- Filtros e auditoria seguem o padrão dos demais admins.

## Não fazer

- Não permitir baixa sem competência (nem “cair” em uma fechada).
- Não aceitar transação `'nenhum'` na baixa.
- Não preencher banco **e** caixa na mesma baixa.
- Não duplicar o movimento quando a baixa é re-salva.
- Não usar exceção crua na tela: erros vão nos campos, com texto amigável.

## Como testar

Em transação com rollback:
1. baixa com transação de **banco** e competência aberta → gera **1** saída em
   `MovimentoBancario` e recalcula o saldo da competência;
2. a mesma baixa com competência bancária **fechada** → recusada com mensagem;
3. baixa com transação de **caixa** e competência de caixa aberta → gera **1**
   saída em `MovimentoCaixa` e desconta do saldo do caixa;
4. baixa com caixa **fechado** → recusada;
5. baixa sem competência → recusada;
6. salvar a mesma baixa duas vezes → **não** duplica o movimento.

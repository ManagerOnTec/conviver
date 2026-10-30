# admin_tesouraria — instruções

Caixa da tesouraria: espelho do `admin_financeiro`, trocando *banco* por
*caixa*. Segue o **Padrão obrigatório dos admins** do `AGENTS.md`.

## Fluxo de negócio

1. **Controle de Caixa** (`ControleCaixa`) — o caixa físico, **por
   estabelecimento** e com **operador** (usuário responsável). Único por
   (descrição + estabelecimento).
2. **Competência de Caixa** (`CompetenciaCaixa`) — o período do caixa.
   **Um caixa tem no máximo UMA competência aberta.** Abertura com
   `saldo_inicial` (fundo de troco) e `saldo_anterior` herdado da última
   competência **fechada** do caixa.
3. **Movimentos de Caixa** (`MovimentoCaixa`) — entradas e saídas. Sempre
   atualizam `saldo_atual` da competência
   (`saldo_inicial + Σ entradas − Σ saídas`).
4. **Conferência de Caixa** (`ConferenciaCaixa`) — dinheiro **contado** ×
   sistema (quebra/sobra). É o equivalente à conciliação bancária.
5. **Fechamento** — só com a conferência **finalizada** e saldo não negativo.

Ordem do menu:
1. Controles de Caixa · 2. Competências de Caixa · 3. Movimentos de Caixa ·
4. Conferências de Caixa.

## Transações de transferência (depósito / saque)

No cadastro de `TransacaoFinanceira` o campo `movimento` tem, além de
`caixa`/`banco`, as opções de **transferência**:

| Movimento | Tipo OBRIGATÓRIO | Onde se LANÇA | O sistema gera |
|---|---|---|---|
| `deposito` — **Depósito Bancário (Caixa → Banco)** | **`deposito_bancario`** | **no CAIXA** (saída) | **entrada** no banco |
| `saque` — **Saque Bancário (Banco → Caixa)** | **`saque_bancario`** | **no BANCO** (saída) | **entrada** no caixa |

**Regra do sentido**: o `tipo` próprio da transferência (`Depósito Bancário` /
`Saque Bancário`) define os dois lançamentos. A transferência é SEMPRE lançada
no lado de onde o dinheiro SAI; o lado que RECEBE (a entrada) é criado
automaticamente no outro módulo, com o mesmo `transferencia_id` — excluir um
lado apaga o par.

Os tipos `entrada`, `saida` e `nenhum` ficam para os movimentos simples de
caixa/banco; **nunca** para transferências.

Consequências práticas:
- **depósito**: lançado no Caixa; `CompetenciaBancaria` é o banco de destino.
- **saque**: lançado no Movimento Bancário; `caixa de destino`
  (`competencia_caixa`) é obrigatório e a **entrada no caixa** é gerada.
- Não digitar saque no caixa nem depósito no banco — o sistema avisa e diz
  onde lançar.

## Regras obrigatórias (invariantes)

- **Transação pode movimentar caixa**: `movimento` em
  (`caixa`, `deposito`, `saque`). Mensagem: *"Escolha uma transação que
  MOVIMENTE CAIXA (ou de DEPÓSITO/SAQUE, que movimentam caixa e banco)."*
- **Origem × transação têm de casar**: no **caixa** só se digita
  `origem='deposito_banco'` com transação `deposito`; o `origem='saque_banco'`
  que aparece no caixa é o **par automático** do saque lançado no banco (não
  pode ser digitado). Transferência exige transação de depósito/saque.
- O par criado pelo sistema é gravado com `_automatico=True` — ele **não**
  gera o lançamento de volta (senão a transferência entraria em loop).
- **Um valor só** — entrada **ou** saída (nunca os dois, nunca negativo), e o
  `tipo` (E/S) tem de casar com o valor.
- **Competência de caixa aberta e data no período** — recusa em caixa fechado:
  *"O caixa «X» está FECHADO: não aceita lançamentos."*
- **Um caixa aberto por vez** — `CompetenciaCaixa.clean`.
- **Fechar exige conferência** — `fechar()` recusa sem `ConferenciaCaixa`
  finalizada e recusa saldo negativo.
- **Transferência caixa ⇄ banco é sempre em DOIS lançamentos**:
  - **Depósito** (`origem='deposito_banco'`): **SAÍDA** do caixa + **ENTRADA**
    na competência bancária informada (que precisa estar **aberta**);
  - **Saque** (`origem='saque_banco'`): **ENTRADA** no caixa + **SAÍDA** no
    banco.
  - Os dois lados compartilham `transferencia_id`; **excluir um apaga o par**.
- **Baixa de pagamento em dinheiro** (módulo `admin_pagamentos`): exige
  competência de caixa aberta e gera uma **saída** com `origem='pagamento'`.

## Movimentos de caixa — origens

**Tipos do movimento de caixa**: `E` Entrada · `S` Saída · **`D` Depósito em
Banco** (sai do caixa e entra no banco — é uma saída com tipo próprio, para o
operador identificar a transferência). Depósito aceita `S` ou `D`; saque (par
automático) é sempre `E`; o tipo `D` exige `origem='deposito_banco'`.

| Origem | Efeito no caixa | Exige banco |
|---|---|---|
| `pagamento` | saída | não |
| `recebimento` | entrada | não |
| `deposito_banco` | saída (tipo `S` ou `D`) | sim (competência bancária aberta) + transação **Depósito Bancário** |
| `saque_banco` | entrada | **par automático** do Saque Bancário lançado no banco |
| `troco` | entrada | não |
| `ajuste` | entrada ou saída | não |

## Menu e telas

- Listagem de **Movimentos**: filtros por competência de caixa, origem, tipo,
  competência bancária, transação e status. Na criação, só aparecem
  competências de caixa **abertas**, transações **de caixa** e competências
  bancárias **abertas**.
- Listagem de **Competências**: saldo inicial/anterior/atual, total de
  movimentos e botão **“Fechar caixa”** (`?fechar=1` já traz a data de hoje).
- Ao abrir uma competência, o **saldo anterior** é preenchido com o saldo final
  da última competência fechada do caixa.

## Não fazer

- Não criar movimento de caixa com transação de banco (ou sem transação).
- Não lançar em competência de caixa fechada.
- Não permitir dois caixas abertos no mesmo `ControleCaixa`.
- Não gravar transferência com um lado só: se o banco não estiver aberto, o
  lançamento é **recusado** (não fica meio lançado).
- Não deixar o saldo do caixa negativo no fechamento.
- Não escrever breadcrumb à mão nem mudar a ordem do menu fora do
  `verbose_name_plural` (`"N. Nome"`).

## Integração com outros módulos

- **`admin_financeiro`** — transferências: `MovimentoCaixa` cria/atualiza o
  `MovimentoBancario` do par (import tardio para evitar import circular).
- **`admin_pagamentos`** — `BaixaPagamento` ganhou `competencia_caixa` e gera o
  `MovimentoCaixa` de saída quando a transação é de caixa.

## Como testar

Sempre em transação com rollback. Cenários mínimos:
1. abrir caixa (saldo herdado) e recusar a 2ª competência aberta do mesmo caixa;
2. lançamento com transação de **banco** → recusado;
3. entrada → soma no saldo; saída → subtrai;
4. **depósito** (saída no caixa + entrada no banco) e **exclusão desfazendo o
   par**;
5. fechar sem conferência → bloqueado; com conferência → fechado;
6. lançar em caixa fechado → recusado;
7. nova competência após fechar → permitida e herdando o saldo.

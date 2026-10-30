# admin_financeiro — instruções

Controle bancário: contas → competências → movimentos → conciliação com extrato.
Segue o **Padrão obrigatório dos admins** do `AGENTS.md` (mixin de
estabelecimento, breadcrumb, auditoria, mensagens amigáveis).

## Fluxo de negócio

1. **Controle bancário** (`ControleBancario`) — uma conta do banco.
2. **Competência bancária** (`CompetenciaBancaria`) — o período de trabalho do
   banco. **Um banco (controle bancário) tem no máximo UMA competência aberta.**
3. **Movimentos** (`MovimentoBancario`) — entradas e saídas. Todo movimento
   pertence a uma competência e atualiza os saldos dela (`recalcular_saldos`:
   `saldo_atual = saldo_anterior + Σ entradas − Σ saídas`).
4. **Conciliação** (`ExtratoImportado` → `LinhaExtrato` → `ConciliacaoBancaria`)
   — importa o extrato (OFX/PDF), casa linha × movimento e **finaliza**.
5. **Fechamento** — só permitido com a conciliação finalizada e **sem
   divergência**; depois de fechada, a competência não aceita mais lançamentos
   e a próxima do mesmo banco pode ser aberta.

6.TransacoesFinanceiras: relação caixa e banco:
-no cadastro de transacoes, movimento tem que ter tipo deposito, tipo saque, e sempre a transacao correspondente nestes casos, porque vai gerar um movimento de entrada caixa e saida banco, ou saida caixa e entrada banco, ajuste transacoes pra ter o tipo e nestes cenarios ter a correspondente, revise tambem o movimento no caixa e no banco neste cenario.

Ordem do menu (por `verbose_name_plural`):
1. Controles Bancários · 2. Competências Bancárias · 3. Movimentos Bancários ·
**4. Conciliação Bancária** (tela própria, não é ModelAdmin — entra por
`_telas_extras` em `managerontec/admin_site.py`, URL `/conciliacao-bancaria/`).

## Regras obrigatórias (invariantes)

- **Competência fechada não recebe nada** — nem criação nem alteração de
  movimento. Mensagem:
  *"A competência «X» está FECHADA em dd/mm/aaaa: não é possível lançar nem
  alterar movimentos dela. Abra uma nova competência para o banco."*
- **Data dentro do período** — `dt_movimento` entre `dt_abertura_competencia` e
  (fechamento ou hoje). Mensagem: *"A data dd/mm/aaaa está fora do período da
  competência «X» (aberta em dd/mm/aaaa)."*
- **Um fechamento por banco** — abrir nova competência exige fechar a anterior
  do mesmo controle bancário (validado em `CompetenciaBancariaForm.clean`).
- **Saldo herdado** — ao abrir, o saldo anterior vem da última competência
  fechada do banco (`anexar_saldo_anterior`); se o usuário digitar outro valor,
  **avisar** a divergência (não bloquear).
- **Fechar exige conciliação** — `fechar()` recarrega a conciliação do banco e
  recusa quando: não existe extrato, não está finalizada ou
  `|divergência| >= 0,01`. Mensagem diz o que falta.
- **Divergência é dinheiro** — nunca “arredondar” ou esconder; a tela mostra
  sistema × extrato × diferença.
- **Regra maior do fluxo** — **competência FECHADA trava tudo**: não se
  lança, altera nem exclui movimento; e, por tabela, trava baixa, fatura,
  pré-fatura e convênio (`motivo_recusa_edicao()` de cada modelo).
- **Exclusão de movimento** — só com a competência bancária **ABERTA**
  (`MovimentoBancario.motivo_recusa_exclusao()`, checado também no
  `delete()` do modelo e no admin). Mensagem: *"A competência “X” está
  FECHADA em dd/mm/aaaa: não é possível excluir movimentos dela. (Para
  corrigir, é preciso reabrir a competência.)"*
- **Valor negativo** — permitido **só em movimento de AJUSTE/estorno**
  (`origem`/`observacao` explicando). No *saldo da fatura* e no `valor_baixa`
  nunca é negativo.

## Movimentos bancários

- `save()`/`delete()` **sempre** recalculam os saldos da competência
  (`competencia_bancaria.recalcular_saldos()`).
- **Baixa de fatura** gera entrada automaticamente (`BaixaFatura.save`), com
  `baixa_fatura` e `origem` preenchida.
- **Exclusão do movimento** — exige competência ABERTA e o movimento NÃO
  conciliado. O saldo do banco é recalculado. Se o movimento veio de uma
  baixa de fatura, a **tela de confirmação pergunta** (radios
  `excluir_baixa_junto`): *Sim* → a baixa é excluída junto e o valor volta ao
  saldo da fatura; *Não* → só o movimento sai e a baixa permanece (pode ser
  excluída depois, em “4. Baixa de Faturas”).
- **Baixa de pagamento** gera saída (`BaixaPagamento.save`), com
  `baixa_pagamento`.
- **Transferência caixa ⇄ banco** — o par é criado pelo `admin_tesouraria`
  (`MovimentoCaixa`); os dois lados compartilham `transferencia_id`. O lado
  banco nasce de uma transação com `movimento` **`deposito`** (entrada no
  banco) ou **`saque`** (saída no banco). O admin de movimentos oferece
  transações de `banco`, `deposito` e `saque`.
- **Lançamento manual** (sem vínculo): usuário escreve a `observacao`; o admin
  prefixa *“Lançamento manual – ”* (sem duplicar na edição).
- **Empacotar Movimentos (Dois ou mais)** — soma os selecionados em um
  lançamento único e **exclui** os demais. Recusas obrigatórias:
  - menos de 2 selecionados;
  - competências diferentes;
  - entradas e saídas misturadas;
  - lançamento que **já é origem de pacote** (não pode ser empacotado de novo).
- Coluna **Conciliação** na listagem: Conciliado / Pendente / Ignorado / Não
  conciliado.

## Conciliação bancária (tela própria — item 4)

URLs: `/conciliacao-bancaria/` (escolha da competência + importação) e
`/conciliacao-bancaria/<id>/` (linhas × movimentos).

1. Escolher a **competência aberta** (o rótulo traz banco/agência/conta).
2. **Importar** extrato **OFX** (SGML, parser em `extrato_parser.py`) ou
   **PDF** (Sicoob ou genérico). Dedupe por `fitid`; saldo final lido do
   arquivo.
3. **Sugerir conciliações** (data + valor), **lançar movimentos das linhas
   pendentes**, conciliar/ignorar selecionadas.
4. **Finalizar** — exige 0 pendentes e divergência < R$ 0,01.
5. **Reabrir** — permitido enquanto a competência não estiver fechada.
6. Depois de finalizada, a competência pode ser **fechada** (ação em lote ou
   botão “Fechar competência”, que abre o form com a data de hoje).

Mensagens-chave: *"Existem N linha(s) do extrato ainda pendente(s)…"*,
*"Divergência de R$ X entre o sistema (R$ A) e o extrato (R$ B)…"*,
*"A competência já está FECHADA…: reabra a competência antes de reabrir a
conciliação."*

## Menu e telas

- **Movimentos**: filtro de competência em *dropdown com busca*
  (`admin/filter_select2.html`) listando **abertas e fechadas**; filtro de
  Banco **múltiplo** (`admin/filter_multiselect.html`) com padrão = banco com
  competência aberta (sem padrão → não restringe e avisa).
- KPIs dos movimentos: Entradas, Saídas, Resultado (E−S), Lançamentos.
- **Competências**: coluna “Fechamento” com botão *Fechar competência*
  (`?fechar=1` pré-preenche a data de hoje e avisa para ajustar).

## Não fazer

- Não criar tela de conciliação dentro do admin de competência.
- Não deixar o usuário escolher competência **fechada** em nenhum form/lançamento.
- Não gravar movimento sem recalcular o saldo da competência.
- Não usar `raise PermissionDenied` cru para usuário logado (mensagem amigável).
- Não escrever breadcrumb à mão: use o include padrão.
- Não importar `admin_tesouraria` no topo de `admin_financeiro` (import circular):
  use import tardio dentro do método.

## Como testar

- Sempre em `with transaction.atomic():` + `raise RuntimeError('rollback')`.
- Cenários mínimos:
  1. abrir competência (saldo herdado) e recusar a 2ª aberta do mesmo banco;
  2. lançar movimento fora do período → recusa;
  3. competência fechada → recusa lançamento;
  4. importar OFX (174 linhas no arquivo de exemplo) → lançar → conciliar →
     fechar;
  5. fechar sem conciliação → bloqueado; com divergência → bloqueado.
- `python manage.py check` antes de concluir.

# admin_pagamentos — instruções

Fluxo de **SAÍDA** (contas a pagar): espelha o fluxo de ENTRADA de
`admin_faturas`. Segue o **Padrão obrigatório dos admins** do `AGENTS.md`.

## Fluxo de negócio

```
Fornecedor → AcordoPagamento → PrePagamento → Pagamento → BaixaPagamento → Movimento
```

1. **Acordo de Pagamento** (`AcordoPagamento`, antes `ParametrosPagamentos`) —
   o contrato/recorrência. Botão **“Gerar previsões”** cria uma
   `PrePagamento` por competência.
2. **Pré-Pagamento** (`PrePagamento`) — a previsão da competência
   (`valor`, `competencia`, `dt_vencimento`). Botão **“Gerar pagamento”**
   cria o `Pagamento`.
3. **Pagamento** (`Pagamento`) — a obrigação CONFIRMADA
   (`valor_pagamento`, `valor_saldo`). Herda de `PrePagamento` (**multitable**:
   a pk do pagamento é o `prepagamento_ptr`). Botão **“Finalizar”** trava
   edição/exclusão; **“Reabrir”** destrava.
4. **Baixa de Pagamento** (`BaixaPagamento`) — a SAÍDA efetiva. Fica no
   **MODAL “Baixas (n)”** da linha do pagamento (a tela própria
   `7. Baixa de Pagamentos` é só histórico/consulta).
5. **Movimento** — a baixa gera **`MovimentoBancario` (saída)** quando a
   transação movimenta BANCO, ou **`MovimentoCaixa` (tipo 'S')** quando
   movimenta CAIXA.

## Regras de EDIÇÃO e EXCLUSÃO (cada etapa olha UM passo à frente)

| Etapa | Só altera/exclui quando… | Mensagem |
|---|---|---|
| **Acordo** | **não** tem pré-pagamento gerado | *“O acordo de pagamento “X” já gerou PREVISÃO e não pode ser alterado/excluído. Exclua primeiro a PREVISÃO, em “5. Pré-Pagamentos”.”* |
| **Pré-Pagamento** | **não** tem pagamento gerado | *“A previsão N já gerou o PAGAMENTO M e não pode ser alterada/excluída. Exclua primeiro o PAGAMENTO, em “6. Pagamentos”.”* |
| **Pagamento** | **aberto** (`finalizado=False`) e **sem baixa** | *“O pagamento N está FINALIZADO…”* / *“O pagamento N já tem baixa registrada…”* |
| **Baixa** | a **competência** (bancária ou de caixa) está **ABERTA** | *“A competência X “Y” está FECHADA em dd/mm/aaaa: não é possível excluir a baixa (nem o movimento dela).”* |

- **`previsto_fechado`** → fica no **Pré-Pagamento** (marcado quando ele já
  gerou o pagamento: a partir daí quem manda é o Pagamento).
- **`finalizado`** → fica no **Pagamento** (a trava do fluxo, espelho do
  `faturado` da Fatura).

## A regra maior: competência FECHADA trava tudo

**Competência bancária fechada** trava: movimento, baixa, pagamento,
pré-pagamento e acordo.
**Competência de caixa fechada** trava do mesmo jeito (a baixa em caixa).

Ordem de liberação (de baixo para cima):

1. reabrir a **competência** (banco ou caixa);
2. excluir o **movimento** (o saldo do banco/caixa é recalculado);
3. excluir a **baixa** (devolve o valor ao `valor_saldo` do pagamento);
4. **reabrir** o pagamento (botão “Reabrir”) e então editar/excluir;
5. excluir a **pré-pagamento** (só sem pagamento);
6. excluir o **acordo** (só sem pré-pagamento).

## Alteração/exclusão EM CADEIA — do maior para o menor

- **Pagamento aberto e sem baixa** → pode ser **excluído**. Ao excluir o
  pagamento, a **pré-pagamento dele sai junto** (ela existe só para gerá-lo).
  Mensagem: *“Pagamento N excluído. A previsão M (que o originou) também foi
  excluída.”*
- **Pré-pagamento** → **NÃO pode ser excluída nem “reaberta”** enquanto o
  pagamento existir. Uma vez que gerou o pagamento, **quem a controla é o
  Pagamento**: só volta a ser editável/excluível depois que o pagamento sair.
- **Acordo** → só sai quando não houver **nenhuma** pré-pagamento ligada.

Ou seja, a exclusão **sobe de baixo para cima** e a **criação desce de cima
para baixo**:

```
CRIAR:    Acordo ──► Pré-Pagamento ──► Pagamento ──► Baixa ──► Movimento
EXCLUIR:  Acordo ◄── Pré-Pagamento ◄── Pagamento ◄── Baixa ◄── Movimento
```

## BAIXA ⇄ MOVIMENTO são CONCOMITANTES

- `BaixaPagamento.excluir_com_movimento()` apaga a baixa **e** os movimentos
  dela (se algum estiver barrado, **nada sai** e o motivo volta);
- `excluir_devolvendo_saldo()` apaga a baixa, apaga o movimento e **devolve
  o valor ao `valor_saldo` do pagamento** (sem isso o pagamento ficaria
  “pago” sem saída);
- excluir pelo **movimento** (`admin_financeiro`) também leva a baixa.

## MODAL de baixas (não há tela própria para lançar)

- O modal abre **somente em pagamento FINALIZADO** — pagamento aberto ainda
  não é conta a pagar. Mensagem: *“O pagamento N está ABERTO e ainda não pode
  receber baixas. Finalize o pagamento primeiro.”*
- Resumo sempre recalculado do banco: **valor do pagamento**, **soma das
  baixas** e **saldo**.
- A baixa escolhe o **destino pela transação**: `movimento='banco'` →
  competência bancária (obrigatória, **aberta**); `movimento='caixa'` →
  competência de caixa (obrigatória, **aberta**). **Nunca os dois.**
- Regra de valor: **> 0** e **≤ saldo** do pagamento.

## Menu e telas (ordem)

- `1. Classificação Fornecedores`
- `2. Classificação Pagamentos`
- `3. Fornecedores`
- `4. Acordos de Pagamento` — botões **Gerar previsões** e **Duplicar**
- `5. Pré-Pagamentos` — botão **Gerar pagamento**
- `6. Pagamentos` — botões **Finalizar/Reabrir** e **Baixas (n)**
- **`7. Baixa de Pagamentos`** — **NÃO** está no menu: a baixa é feita
  apenas pelo **modal “Baixas (n)”** do Pagamento.

## Duplicar acordo (nova DESPESA)

Mesma regra do **Duplicar** do `AcordoFaturamento`:

- o botão só fica ativo depois que o acordo **gerou as previsões**
  (`pre_pago=True`); antes disso sai **cinza**;
- a ação cria um **acordo NOVO** copiando o contrato
  (`fornecedor`, `classificacao_pagamento`, `valor_previsto`,
  `dia_pagamento`, `recorrencia`, `data_inicio`, `data_fim`,
  `forma_pagamento`, `observacao`), com:
  - `pre_pago = False` — **nenhuma previsão** é copiada (a nova despesa
    começa do zero, pronta para o botão “Gerar previsões”);
  - `status = 'A'` e auditoria do usuário atual;
- o acordo de **origem é inativado** (`status = 'I'`) — mantém o histórico
  das previsões/pagamentos que gerou;
- a tela cai no formulário do **novo** acordo.

Mensagem: *“Acordo de pagamento duplicado: novo acordo N (o original M foi
inativado).”*

## Retenções (percentual + valor fixo)

O `AcordoPagamento` tem **duas retenções**, espelhando o
`AcordoFaturamento`:

| Campo | Significado |
|---|---|
| `tx_retencao` | **percentual** descontado do valor bruto |
| `vl_retencao` | **valor FIXO** descontado **depois** do percentual |

**Ordem do cálculo** (`calcular_retencao` / `valor_liquido`):

```
retencao_pct   = valor * (tx_retencao / 100)
liquido        = valor - retencao_pct - vl_retencao
```

- **Campo em branco não entra no cálculo**: sem `tx_retencao` não há
  desconto percentual; sem `vl_retencao` não há desconto fixo; sem os dois
  o valor a pagar é o bruto.
- A retenção **nunca** ultrapassa o valor (resulta em 0 no mínimo).
- `gerar_previsoes()` **congela** `tx_retencao`/`vl_retencao` na
  `PrePagamento` (como a pré-fatura faz com o acordo).
- `PrePagamento.gerar_pagamento()` grava como `valor_pagamento` e
  `valor_saldo` o **valor LÍQUIDO** (`valor_liquido()`) — é o valor que a
  baixa abate.

Exemplo: valor 1.000, `tx_retencao=10`, `vl_retencao=50` →
retenção 100 + 50 = **150** → paga-se **850**.

## Indicadores (KPIs) e filtros personalizados

Cada tela do fluxo segue o **seed do fluxo de faturas**
(`admin_faturas/dashboard.py`): mixin próprio em
`admin_pagamentos/dashboard.py` (`PagamentosDashboardMixin`, herdado de
`AdminDashboardAndTopFilterMixin`) + `get_dashboard_kpis` em cada admin.

| Tela | KPIs |
|---|---|
| Acordos | Acordos · Em Vigor · Valor Previsto · Pré-Pagos/Sem previsão |
| Pré-Pagamentos | Pré-Pagamentos · Valor Total · A Gerar Pagamento · Vencidas sem Pagamento · Já Geraram Pagamento |
| Pagamentos | Pagamentos · Valor dos Pagamentos · Pago · Total Saldo em Aberto · Saldo Vencido em Aberto |

- **Presets de período**: Competência do mês, Competência anterior, Venc.
  do mês, Vencidas, A vencer (via `get_top_filter_presets`).
- **Atalhos**: Todos/Ativos/Inativos; Em aberto/Quitados (só onde há
  `valor_saldo`); Pré-Pagos/Sem previsão (`pre_pago`);
  Finalizados/Abertos (`finalizado`).
- **Dropdown do topo**: **Fornecedor** (`FornecedorPagadorFilter`,
  parâmetro `fornecedor_pagador`).
- Todos os filtros novos ficam dentro de `try/except` (AGENTS.md, item 9).

## Fechar o modal ATUALIZA a listagem (preservando filtros)

O `static/js/admin_baixas_modal.js` marca `houveAlteracao` quando o POST
volta renderizado (baixa lançada ou excluída) e, ao **fechar** o modal
(`✕`, Esc ou clique fora), chama `window.location.reload()`. O reload
**preserva a query string inteira** — busca, período, atalhos, dropdown e
paginação continuam aplicados — e a listagem volta com o **saldo** e o
**contador “Baixas (n)”** recalculados.

Os filtros **só zeram** pelo botão **“✕ Limpar Todos os Filtros”**, que
está **sempre visível** na barra de filtros (esmaecido quando não há filtro
ativo).

## EDIÇÃO EM LINHA (list_editable) — a mesma regra da tela

A listagem editável **é edição**: vale `motivo_recusa_edicao()` igual ao
formulário. Exige **duas coisas** no ModelAdmin — sem qualquer uma delas o
Django cai na tabela padrão e as colunas seguem editáveis (sem o cadeado):

```python
list_editable_sempre = [...]          # colunas declaradas
list_editable = list_editable_sempre

def get_changelist(self, request, **kwargs):
    from admin_faturas.changelist_editavel import ChangeListEditavel
    return ChangeListEditavel       # ← sem ISTO não há cadeado

def get_linhas_nao_editaveis(self, request):
    ...                             # pks das linhas travadas
```

| Tela | Linhas somente leitura |
|---|---|
| Acordo | com previsão gerada (`PrePagamento.acordo_pagamento`) |
| Pré-Pagamento | com pagamento gerado (`Pagamento.prepagamento_ptr_id`) |
| Pagamento | **finalizado** (`finalizado=True`) ou com baixa |

- Nas linhas travadas as colunas editáveis viram **TEXTO** (o valor
  continua visível), com o motivo no `title`: *“Linha travada pelo fluxo: o
  valor não pode ser alterado aqui.”*
- Recorte “Pré-Pagos” / ”Finalizados” no filtro do topo → nenhuma linha
  editável (`list_editable_permitido` devolve `[]`).
- O `get_changelist` precisa estar **dentro** da classe do admin: um método
  com a mesma indentação numa classe vizinha vale para ela, não para a
  pretendida (erro silencioso — a tela volta a ser `ChangeList` padrão).

## Botões personalizados — ordem no início da listagem

`id → botões de função → excluir → dados` (AGENTS.md, item 10). No acordo:
`id, Gerar previsões, Duplicar, excluir, …`

## Modal de baixas — obrigatório

- O botão **“Baixas (n)”** do pagamento precisa ter a classe
  `js-baixas-modal` e `data-url` — é o `static/js/admin_baixas_modal.js`
  que ESCUTA essa classe e carrega o modal por `fetch`. Sem a classe o
  clique navega para a página inteira (o modal “não abre”).
- O conteúdo é `admin_pagamentos/baixas_do_pagamento.html` (raiz
  `.baixas-wrap`, que é o que o JS extrai).
- O form do modal recebe o **pagamento pela URL** (`pagamento=pag`),
  não pelo POST: `pagamento` sai como `required=False` e a auditoria
  (`us_registro`/`dt_registro`) é gravada pelo admin.
- `dt_pagamento` usa `type="date"` (calendário do navegador).

## Sem menu “7. Baixa de Pagamentos”

A baixa é feita **somente pelo modal**. O `BaixaPagamentoAdmin` continua
definido no arquivo (as baixas continuam acessíveis pelo modal do
Pagamento), mas o modelo **não é registrado** — `admin.site.register(
BaixaPagamento, …)` fica comentado, então o item “7. Baixa de Pagamentos”
não aparece no menu e a URL da changelist responde 404.

Mesmo padrão de `admin_faturas`, onde `BaixaFaturaAdmin` também existe mas
o modelo não é registrado.

## Não fazer

- Não lançar baixa em pagamento **aberto**.
- Não permitir baixa sem competência, nem “cair” em uma fechada.
- Não aceitar transação `'nenhum'` na baixa.
- Não preencher banco **e** caixa na mesma baixa.
- Não duplicar o movimento quando a baixa é re-salva.
- Não deixar exceção crua na tela: erros viram mensagem no campo/linha.
- Não criar tela/menu separado para Baixa de Pagamentos: é só o modal.
- Não esquecer a classe `js-baixas-modal` no botão de baixas.

## Como testar

Em `with transaction.atomic():` + `raise RuntimeError('rollback')`:

1. acordo sem previsão → **pode excluir**; com previsão → bloqueado;
2. `gerar_previsoes()` cria N previsões e trava o acordo;
3. `PrePagamento.gerar_pagamento()` cria o Pagamento e trava a previsão;
4. pagamento **aberto** → excluível; **finalizado** → bloqueado;
5. reabrir com baixa → **recusado**;
6. baixa com competência **aberta** → gera `MovimentoBancario` com
   `valor_saida` e desconta o saldo;
7. excluir a baixa → movimento sai e o **saldo volta**;
8. competência **fechada** → baixa e movimento recusados;
9. **duplicar acordo** com previsões → novo acordo (`pre_pago=False`, sem
   previsões) e o original fica `status='I'`;
10. **retenções**: acordo com `tx_retencao=10` e `vl_retencao=50` sobre
    1.000 → previsão/pagamento com **850**; em branco → 1.000;
11. menu **sem** “7. Baixa de Pagamentos”; botão de baixas com
    `js-baixas-modal`;
12. **modal**: lançar/excluir e fechar → a listagem recarrega mantendo os
    filtros e o contador “Baixas (n)”;
13. **indicadores**: as três listagens (acordo, pré-pagamento, pagamento)
    mostram os KPIs e os presets de período;
14. **filtro de fornecedor** válido e inexistente → 200 (não derruba);
15. **list_editable**: acordo com previsão / previsão com pagamento /
    pagamento finalizado ou com baixa → a listagem mostra as colunas em
    TEXTO (classe `celula-travada`), não como campo editável;
16. `python manage.py check` antes de concluir.

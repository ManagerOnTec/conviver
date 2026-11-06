# admin_faturas — instruções

Fluxo: **Acordo de Faturamento → Pré-Fatura → Fatura → Baixa de Fatura**. Segue o
**Padrão obrigatório dos admins** do `AGENTS.md`.

## Fluxo de negócio

1. **Acordo de Faturamento** (`AcordoFaturamento` / `AcordoFaturamento`) — contrato; gera as pré-faturas por competência. Na listview, `nr_contrato`, `nr_aditivo`, `inicio_vigencia`, `final_vigencia`, `tx_retencao_nf` e `vl_retencao_nf` também são editáveis, sujeitos à regra de edição abaixo.
2. **Pré-Fatura** (`PreFatura`) — lançamento do acordo (`create_fatura()`
   vira a fatura).
3. **Fatura** (`Fatura`) — herda de `PreFatura` (multitable: a pk da fatura é o
   `prefatura_ptr`). Aberta (`faturado=False`) → finalizada (`faturado=True`).
4. **Baixa de Fatura** (`BaixaFatura`, item 4) — recebimento; abate
   `valor_saldo` da fatura e gera o movimento bancário.

### Filtro superior de pagador
- Na changelist de Pré-Faturas/Faturas, opções de pagador são derivadas dos registros dessas telas (inclusive acordos inativos/históricos), usando o pagador do próprio registro ou, se estiver nulo, o do acordo.
- Ao filtrar, corresponde ao pagador gravado na Pré-Fatura/Fatura; usa o pagador do acordo como fallback somente quando o snapshot do registro está nulo. Não incluir registros com pagador explicitamente diferente.
- Na changelist de Acordos, as opções continuam derivadas dos acordos ativos.

## Regras de EDIÇÃO e EXCLUSÃO (prevalecem sobre o resto)

Cada etapa olha **somente UM passo à frente**. Não há mais regra em cascata.

| Etapa | Só pode ser alterada / excluída quando… | Mensagem |
|---|---|---|
| **Acordo de Faturamento** | **não** tem pré-fatura ligada a ele | *“O acordo de faturamento “X” já tem pré-fatura gerada e não pode ser alterado/excluído. Exclua primeiro a PRÉ-FATURA (“2. Pré-Faturas”)…”* |
| **Pré-Fatura** | **não** tem fatura ligada a ela | *“A pré-fatura N já gerou a fatura M e não pode ser alterada/excluída. Exclua primeiro a FATURA, em “3. Faturas”…”* |
| **Fatura** | **não** tem baixa de fatura ligada a ela | *“A fatura N tem baixa registrada e não pode ser alterada/excluída. Exclua primeiro a BAIXA, em “4. Baixa de Faturas”…”* |
| **Baixa de Fatura** e **Movimento** | a **competência bancária** está **ABERTA** | *“A competência bancária “X” está FECHADA em dd/mm/aaaa: não é possível alterar/excluir a baixa…”* |

Implementação (`motivo_recusa_edicao` / `motivo_recusa_exclusao`):

- `AcordoFaturamento` — `self.prefaturas.exists()`;
- `PreFatura` — `Fatura.objects.filter(prefatura_ptr_id=self.pk)`;
- `Fatura` — `self.baixas_registradas().exists()`;
- `BaixaFatura` e `MovimentoBancario` — `dt_fechamento_competencia` da
  competência (a baixa olha a própria e a dos movimentos gerados).

As mesmas regras valem na **listagem editável** (`get_linhas_nao_editaveis`) e
na **ação em lote** — não repetir a condição em outro lugar.

## FLUXO CONTÍNUO — edição e exclusão (regra única)

Cada etapa só muda enquanto **nenhuma etapa à frente estiver fechada /
finalizada**. A regra mora no modelo (`motivo_recusa_edicao()`), e o admin
(`EdicaoComRegrasMixin`) transforma o impedimento em mensagem + volta para a
listagem — nunca 403 nem debugger.

| Etapa | Pode ALTERAR quando | Pode EXCLUIR quando |
|---|---|---|
| Convênio | sem pré-fatura gerada; com pré-fatura SÓ se nada adiante estiver travado | sem pré-fatura gerada |
| Pré-Fatura | sem fatura gerada; com fatura só enquanto ela estiver aberta E sem movimento/baixa | sem fatura gerada (ou pela regra da fatura) |
| Fatura | **aberta** (`faturado=False`), sem baixa e sem movimento | aberta e sem baixa/movimento |
| Baixa | sem movimento gerado e sem competência fechada | movimento já excluído (devolve o valor ao saldo) |
| Movimento | competência **aberta** (e não conciliado, p/ excluir) | competência **aberta** |

**A regra maior: competência bancária FECHADA trava tudo** (movimento, baixa,
fatura, pré-fatura e convênio). Ordem de liberação (de baixo para cima):

1. competência aberta → excluir **movimento** (saldo do banco recalculado);
2. excluir **baixa** (devolve o valor ao saldo da fatura);
3. editar/excluir **fatura** (precisa estar aberta: desmarque “faturado”);
4. editar/excluir **pré-fatura** (só sem fatura gerada);
5. editar/excluir **convênio** (só sem pré-fatura).

Mensagens-chave: *“A competência “X” está FECHADA em dd/mm/aaaa: ela trava …”*,
*“A fatura N está FINALIZADA e não pode ser alterada. Marque-a como NÃO
faturada (Fatura Aberta) para corrigir.”*, *“A baixa N tem movimento bancário
(#M) e não pode ser alterada. Exclua PRIMEIRO o movimento…”*.

## EDIÇÃO EM LINHA (list_editable) — a mesma regra da tela

A listagem editável **é edição**: vale `motivo_recusa_edicao()` igual ao
formulário. Implementação em `dominios/utils.py::ListEditableComRegras`
(herdado por `EdicaoComRegrasMixin`):

- `list_editable_sempre` — colunas declaradas; `list_editable` é recalculado a
  cada requisição (`list_editable_permitido(request)`);
- `get_linhas_nao_editaveis(request)` — pks que saem **somente leitura**
  (texto, sem widget), calculadas **em lote** (1 consulta por tela):

| Tela | Linhas somente leitura |
|---|---|
| Convênio | com pré-fatura gerada |
| Pré-Fatura | com fatura gerada (qualquer estado) |
| Fatura | finalizada ou com baixa/movimento |
| Baixa de Faturas (grade de faturas) | fatura finalizada ou já com baixa |
| Movimento | sem `list_editable` (nada a travar) |

- o `title` do `id`/`pk` da linha travada explica o motivo;
- no POST de `_save`, as linhas travadas são retiradas do formset com aviso
  (`_recusar_edicoes_em_linha`).

## Layout das listagens (AGENTS.md, item 10)

Ordem das sessões, de cima para baixo: **breadcrumb → botões Adicionar/Salvar
→ dashboards (KPIs) → filtros/busca → ações em lote → tabela**.

- **Travadas na rolagem**: breadcrumb, KPIs, filtros e a **barra de ações**
  (`position: sticky`) — a tabela mantém o `<thead>` fixo.
- **Ocultar/exibir** (breadcrumb, filtros, KPIs): `✕ Ocultar` dentro do
  painel, `Indicadores`/`Filtro Topo` na barra de exibição (Alt+K / Alt+T) e no
  dock. Estado salvo em `localStorage` (`conviver_hide_dashboard`,
  `conviver_hide_filters_panel`).
- **Barra de ações e tabela nunca são ocultadas** (regra do item 10).
- **Rolagem horizontal em DOIS lugares**: a do rodapé (nativa) e uma faixa no
  **topo** da tabela (`js-scroll-topo`, sincronizada) — as listas têm ~19
  colunas e ~3500px de largura.

## Cores das mensagens (AGENTS.md, item 6)

`MESSAGE_TAGS` emite as classes do Django **e** as do Bootstrap
(`error alert-danger`, `warning alert-warning`, `success alert-success`), e
`admin_layout_toggles.css` (seções 7 e 10) pinta o `ul.messagelist` e o
`includes/messagelist.html`:

- **sucesso → verde** (`#e7f6ec` / borda `#198754`)
- **alerta → amarelo** (`#fff8e1` / borda `#e0a800`)
- **perigo → vermelho** (`#fdecec` / borda `#dc3545`)
- informação → azul

## Regras obrigatórias (invariantes)

- **Exclusão de FATURA** — `Fatura.motivo_recusa_exclusao()`:
  - FINALIZADA (`faturado=True`) → não pode;
  - COM movimento (existe baixa em `BaixaFatura` apontando para ela) → não pode;
  - aberta (não faturada) e SEM movimento → **pode**.
- **Exclusão de PRÉ-FATURA** — mesma regra: consulta as tabelas da fatura
  gerada (`Fatura.objects.filter(prefatura_ptr_id=self.pk)`); sem fatura
  gerada, pode ser excluída.
- **BAIXA ⇄ MOVIMENTO são CONCOMITANTES** — excluir um exclui o outro,
  **unitário ou em lote**:
  - `MovimentoBancario.delete()` apaga a `BaixaFatura` de origem (padrão) e a
    baixa devolve o valor ao `valor_saldo` da fatura;
  - `BaixaFatura.excluir_com_movimento()` apaga a baixa e os movimentos dela
    (se algum estiver barrado, nada sai e o motivo volta);
  - a tela de confirmação do movimento apenas **avisa** “a baixa será
    excluída junto”; não há mais pergunta sim/não.
- **Quem decide é SÓ a competência bancária**: aberta → pode; fechada → não.
  A fatura estar FINALIZADA **não** impede excluir/alterar baixa ou movimento
  (senão não haveria como desfazer a baixa).
- **Exclusão de BAIXA** (`BaixaFatura.motivo_recusa_exclusao()`) — só a
  **competência bancária fechada** bloqueia: *“A competência bancária “X”
  está FECHADA em dd/mm/aaaa: não é possível excluir a baixa (nem o
  movimento dela). Reabra a competência para corrigir.”* Com a competência
  aberta, a baixa sai levando o MOVIMENTO junto.
  **ALTERAR** a baixa segue a mesma régua (`motivo_recusa_edicao`): fechada
  bloqueia; com movimento pede excluir o movimento primeiro (ele leva a baixa).
  - `BaixaFatura.excluir_devolvendo_saldo()` apaga e **devolve o valor ao
    `valor_saldo` da fatura** (desfazendo a liquidação quando volta a ter
    saldo) — sem isso a fatura ficaria “paga” sem recebimento.
  - Botão **“Excluir baixa”** por linha na listagem de contas a receber
    (`excluir_button`); a confirmação usa `templates/admin/delete_confirmation.html`.
  - `BaixaFaturaAdmin.get_object` aceita a pk da BAIXA **ou** da FATURA da
    linha (a listagem lista faturas).
- **Exclusão de CONVÊNIO** — com pré-fatura gerada (`pre_faturado` ou
  `prefaturas` existentes) **não pode**: primeiro se excluem as faturas e as
  pré-faturas (cada uma com sua própria regra).
- **Exclusão de MOVIMENTO BANCÁRIO** — ver
  `admin_financeiro/instrucoes_financeiro.md` (só competência aberta).
- Todas as recusas viram **mensagem** (`messages.error/warning`), nunca 500:
  `has_delete_permission(obj=...)` recusa a tela de confirmação;
  `delete_model`/`delete_queryset` recusam linha a linha e informam o motivo.

## Ação em lote “Excluir selecionados”

`dominios/utils.py::ExclusaoEmLoteComRegrasMixin` — primeiro mixin dos admins
que têm exclusão. Substitui o `delete_selected` padrão (que apagaria tudo ou
derrubaria a tela com `ProtectedError`):

- cada registro passa pela MESMA regra da exclusão individual
  (`motivo_recusa_exclusao()` do modelo, + `_impedimento_extra_exclusao(obj)`
  do ModelAdmin quando a regra não está no modelo — caso do convênio);
- permitidos: excluídos (uma mensagem de sucesso com o total);
- bloqueados: NÃO são apagados e cada um vira mensagem com o motivo (máx. 10);
- a listagem editável mostra o `pk`/`id` das linhas bloqueadas em CINZA com o
  motivo em `title` (`_Celula.exclusao`, ver `ChangeListEditavel`);
- listagens com `changelist_view` próprio (movimentos) despacham a ação pelo
  `changelist_view_com_acoes` — sem depender do `get_actions` do Django.

Uso: `class XAdmin(ExclusaoEmLoteComRegrasMixin, ..., admin.ModelAdmin)` e
`actions = [..., 'excluir_selecionados']`.

## Mensagens (texto padrão)

- *"A fatura N está FINALIZADA e não pode ser excluída. Se precisar
  corrigi-la, primeiro reabra a fatura."*
- *"A fatura N já tem baixa (recebimento) registrada e não pode ser excluída.
  Exclua primeiro as baixas dela."*
- *"O convênio “X” já tem pré-fatura gerada e não pode ser excluído. Exclua
  primeiro a(s) FATURA(S) e a(s) PRÉ-FATURA(S) dele…"*

## Não fazer

- Não deixar `ProtectedError`/`ValidationError` chegar à tela.
- Não usar `HttpResponseRedirect` cru no meio de `delete_queryset` (as
  mensagens se perdem): recusar linha a linha com `messages` e seguir.

## IMPORTAÇÃO DE ACORDOS (planilha CONVENIOS.xlsx)

**Padrão obrigatório:** acordos importados recebem `modo_fatura='CO'` (um acordo consolidado), independentemente da contagem de clientes na planilha. Não importar como `CL`.

Tela própria em `admin_faturas/importacao.py`, aberta pelo botão
**“Importar planilha”** que fica ao lado de **“Salvar”** na tela de **ADD**
de AcordoFaturamento.

### Regra central: linha repetida é COMPETÊNCIA, não acordo novo

A planilha tem **uma linha por competência**. O mesmo órgão + cliente
aparece em várias linhas: isso é **UM** acordo, e a repetição é a vigência.

```
grupo = (cidade_normalizada, cnpj_limpo, contrato)
inicio_vigencia = min(EMITIDO EM)
final_vigencia  = max(EMITIDO EM)
qtd_competencias = nº de linhas do grupo   (relatório, não é campo)
```

### Colunas lidas

| Col | Campo | Uso |
|---|---|---|
| [1] | CIDADE | vira `Cidade` (UF fixa **SC**); o sufixo depois de ` - ` é o setor e é **descartado** na busca da cidade |
| [2] | CNPJ | vira `Empresa` → `pagador_pj` do acordo |
| [3] | acolhidos | nomes de clientes (não vinculados na importação) |
| [5] | EMITIDO EM | competência; define vigência e `dia_envio` |
| [7] | VALOR | valor da NF daquela competência |
| [10] | DESCRIÇÃO | decisores (abaixo) |

### Decisores da descrição (colunas J e K)

- `CT <n>/<ano>` ou `Contrato: <n>` → `nr_contrato`
- `Empenho <n>` → `empenho_global`
- `Diária de R$ <v>` → `valor_diaria`

**Onde a diária pode estar (procura nesta ordem):**

1. na descrição (coluna J): `Diária de R$ 375,84`;
2. na observação (coluna K);
3. na **FÓRMULA** da coluna de valor, no formato
   `diária × acolhidos × dias`: `=425*9*O$1` → diária 425.

**Como a fórmula é reconhecida (e como NÃO é):**

| Fórmula | Diária | Por quê |
|---|---|---|
| `=425*9*O$1` | 425,00 | 3 fatores (diária, acolhidos, dias) |
| `=11*31*277.52` | 277,52 | tem centavos |
| `=12*J134` | **nenhuma** | só 1 número — o `12` é a QUANTIDADE DE DIAS |
| `92665.91` | **nenhuma** | valor fixo, sem multiplicação |

> Regra: exige **2+ fatores numéricos**; a diária é o fator com centavos
> ou o primeiro quando todos são inteiros. Fórmulas com 1 número só são
> dias × valor e **não** são diária.

### O VALOR É SEMPRE POR CLIENTE (regra central)

A planilha lança, por competência, o **total do grupo**. O sistema fatura
**por cliente** (`valor_mensal` × nº de clientes), então o import DIVIDE:

```
valor_mensal (acordo) = total da nota / nº de clientes da linha
```

- o divisor é `extrair_quantidade(K)` (`9 Pacientes`) ou, sem ele, a
  própria contagem da coluna D;
- `valor_mensal` fica **0** quando o contrato é por diária (o valor real é
  diária × dias × clientes);
- a pré-visualização mostra `valor_total_competencia`, `qtd_clientes` e
  `valor_mensal` (por cliente) separados;
- se o valor **por cliente** muda entre competências → alerta (reajuste);
  se só o **total** muda → alerta informando que o nº de clientes variou.

### Divisor de clientes: `;`, `,` ou quebra de linha

A coluna D usa os três separadores, às vezes na mesma planilha:

```
Valci Maria Lucindo - 31-08-26     (quebra)
Amarildo Forbici; Joao da Silva    (ponto e vírgula)
Ester Amaral, Laura Batista, Kleber (vírgula)
```

**Uma única função** (`_partes_clientes`) divide para CRIAR e para CONTAR.
Se a contagem usasse outra regra, o divisor do valor divergiria da
quantidade de nomes efetivamente criados.

### Diária: como distinguir de um TOTAL repetido

A diária pode estar na coluna J (número puro), na K (`Diária R$ …` ou
apenas `R$ 415,00`) ou na fórmula. A armadilha é a coluna J trazendo o
**total da nota** repetido:

| Grupo | Coluna J | Observação | Diagnóstico |
|---|---|---|---|
| Itajaí (9 cli.) | `415` | `9 Pacientes / R$ 415,00` | DIÁRIA |
| Navegantes (10) | `277.52` | `62 diárias a 277,52 dia` | DIÁRIA |
| Joinville (12) | `8348.28` | sem valor, sem total (H) | **TOTAL** |

Ordem de decisão:

1. K tem `Diária R$ …` → é a diária;
2. K tem `<valor> dia` / `a <valor> dia` → é a diária;
3. K tem `R$ …` → é a diária (quem declara na nota está dando o unitário);
4. senão, o número da coluna J só vale se **NÃO** for ≥ o total (H);
5. fechado o grupo, `refinar_diaria_do_grupo`: número **igual em todas as
   linhas** só é diária se couber em 1 dia de atendimento (≤ R$ 1.000).
   `8348.28` em 8 competências não é preço de 1 dia → descartado.

### CLIENTES (coluna D) — criados e vinculados

A coluna D traz **um acolhido por linha da célula**, no formato
`Nome - dd-mm-aa`:

```
Valci Maria Lucindo - 31-08-26
Marli Moreira de Sa - 16-05-26
```

Cada nome vira uma `Pessoa` com `classificacao_pessoa='paciente'` e
`dt_nascimento` da planilha, e é **vinculado ao acordo** (`acordo.cliente`).

- `rg`/`cpf` vão como `None` (são `UNIQUE`; `''` quebraria no 2º cliente);
- `sexo='f'`/`alergico='N'` são defaults da planilha (não traz o campo) —
  ajustáveis depois na tela do paciente;
- o MESMO nome + nascimento não é duplicado entre acordos.

### LINHA VERMELHA não é competência

As linhas com a **coluna A preenchida de vermelho** (`FFFF0000`) NÃO
entram na vigência: são previsões/futuras, não competências já faturadas.
Elas são **ignoradas** e o total aparece como alerta na pré-visualização:

> *“N linha(s) em VERMELHO na planilha foram IGNORADAS da vigência…”*

### Normalizações obrigatórias

- CNPJ: só os 14 dígitos (aceita `"08259606000158'` com apóstrofo);
- Cidade: sem acento/espaço extra, com título corrigido
  (`itajai` → `Itajaí`, `camboriu` → `Camboriú`);
- Gênero: a mesma cidade em dois CNPJs distintos = **dois** acordos.

### Campos fixos na importação

`modo_fatura='CL'`, `modalidade_contrato='CO'`, `dias_pagamento=30`,
`dia_envio` = dia do primeiro `EMITIDO EM`, `descricao_internacao='acolhimento'`,
retenções zeradas, `estabelecimento` = o da sessão/perfil.

### Fluxo em duas etapas (nada grava na etapa 1)

1. **Upload** → a view lê e mostra: quantos acordos, quantas competências,
   empresas/cidades que serão criadas e as **divergências**;
2. **Confirmar** → grava tudo em **UMA** transação (falha → lote inteiro
   desfeito).

Divergências reportadas sem bloquear: valores diferentes no mesmo grupo
(usa o primeiro) e linhas com CNPJ inválido. Linhas separadoras (`-`) são
ignoradas silenciosamente.

### Não fazer na importação

- Não criar um acordo por linha (a linha é competência);
- Não criar duplicado se a previsão já gerou pagamento — a importação só
  cria acordos **novos**;
- Não confiar em dados do POST na etapa 2: a planilha é **relida** do
  arquivo temporário guardado na sessão.

## Como testar

- Em `with transaction.atomic():` + `raise RuntimeError('rollback')`.
- Cenários: fatura finalizada / com baixa / aberta sem movimento; pré-fatura com
  e sem fatura; baixa associada; convênio com e sem pré-fatura gerada.
- **Importação**: `ler_planilha()` deve agrupar as linhas repetidas em UM
  acordo por `(cidade, cnpj, contrato)`; a prévia NÃO pode gravar nada;
  confirmar deve criar todos em uma transação. Com a `CONVENIOS.xlsx` atual:
  **34 acordos / 246 competências / 79 clientes** (linhas vermelhas
  ignoradas; competências = dias de emissão **distintos** por grupo).
- `python manage.py check` antes de concluir.

# admin_faturas — instruções

Fluxo: **Convênio → Pré-Fatura → Fatura → Baixa de Fatura**. Segue o
**Padrão obrigatório dos admins** do `AGENTS.md`.

## Fluxo de negócio

1. **Convênio** (`Convenio`) — contrato; gera as pré-faturas por competência.
2. **Pré-Fatura** (`PreFatura`) — lançamento do convênio (`create_fatura()`
   vira a fatura).
3. **Fatura** (`Fatura`) — herda de `PreFatura` (multitable: a pk da fatura é o
   `prefatura_ptr`). Aberta (`faturado=False`) → finalizada (`faturado=True`).
4. **Baixa de Fatura** (`BaixaFatura`, item 4) — recebimento; abate
   `valor_saldo` da fatura e gera o movimento bancário.

## Regras de EDIÇÃO e EXCLUSÃO (prevalecem sobre o resto)

Cada etapa olha **somente UM passo à frente**. Não há mais regra em cascata.

| Etapa | Só pode ser alterada / excluída quando… | Mensagem |
|---|---|---|
| **Convênio** | **não** tem pré-fatura ligada a ele | *“O convênio “X” já tem pré-fatura gerada e não pode ser alterado/excluído. Exclua primeiro a PRÉ-FATURA (“2. Pré-Faturas”)…”* |
| **Pré-Fatura** | **não** tem fatura ligada a ela | *“A pré-fatura N já gerou a fatura M e não pode ser alterada/excluída. Exclua primeiro a FATURA, em “3. Faturas”…”* |
| **Fatura** | **não** tem baixa de fatura ligada a ela | *“A fatura N tem baixa registrada e não pode ser alterada/excluída. Exclua primeiro a BAIXA, em “4. Baixa de Faturas”…”* |
| **Baixa de Fatura** e **Movimento** | a **competência bancária** está **ABERTA** | *“A competência bancária “X” está FECHADA em dd/mm/aaaa: não é possível alterar/excluir a baixa…”* |

Implementação (`motivo_recusa_edicao` / `motivo_recusa_exclusao`):

- `Convenio` — `self.prefaturas.exists()`;
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

## Como testar

- Em `with transaction.atomic():` + `raise RuntimeError('rollback')`.
- Cenários: fatura finalizada / com baixa / aberta sem movimento; pré-fatura com
  e sem fatura; baixa associada; convênio com e sem pré-fatura gerada.
- `python manage.py check` antes de concluir.

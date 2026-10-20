# Prescrição Padrão (modelo de prescrição) — 20/10/2026

## O que foi entregue

Na tela `prontuarios/prescricao_cadastrar/<atendimento_id>/` foi criada uma barra
**“Assistente de Prescrição”** logo abaixo de `cabdados`, no mesmo padrão visual do
*Assistente Clínico* de Evoluções (`evolucao-smart-tools-bar` + `clinical-tool-btn`):

```
Assistente de Prescrição:  [ Prescrição Padrão ]
```

O botão abre um modal (`templates/parciais/_prescricao_padrao_modal.html`) que lista os
modelos cadastrados em **Admin → Prescrição Padrão**, respeitando:

1. **`ParametrosPrescricao`** — o usuário precisa ter parâmetro ativo (por profissional
   ou por profissão) no estabelecimento da sessão, ou ser superusuário. É o mesmo
   critério que já libera o cadastro de prescrição (`PrescricaoForm.clean`).
2. **Liberação do próprio modelo** (`PrescricaoPadrao.pode_ser_usada_por`):
   - sem profissional/profissão → qualquer profissional com parâmetro de prescrição;
   - com profissional → apenas ele;
   - com profissão → qualquer profissional daquela profissão.

Ao clicar em **Inserir**, os itens do modelo são **acrescentados** ao formset da
prescrição em montagem (produto, intervalo, hora de início, se necessário, dose única,
observação), exatamente nos mesmos campos do formset existente. A lógica original de
“Adicionar Item”/remover item **não foi alterada**.

> O item inserido envia um hidden `produtos-<n>-item_padrao_id`. A view remove esse
> campo da cópia usada pelo formset principal e o usa apenas para gravar a auditoria
> `PrescricaoPadraoUtilizacao` (consulta somente leitura no admin).

## Modelos (app `admin_prescricoes`)

Todo o domínio de prescrição padrão vive em **`admin_prescricoes`** — não em
`prontuarios`. Os arquivos são separados de `models.py`/`forms.py`/`views.py` apenas
para manter a funcionalidade isolada e removível:

| Arquivo (em `admin_prescricoes/`) | Conteúdo |
|---|---|
| `models_prescricao_padrao.py` | `PrescricaoPadrao`, `ProdutoPrescricaoPadrao`, `PrescricaoPadraoUtilizacao` |
| `forms_prescricao_padrao.py` | `PrescricaoPadraoForm`, `ProdutoPrescricaoPadraoForm`, `ProdutoPrescricaoPadraoFormSet` |
| `views_prescricao_padrao.py` | `PrescricoesPadraoDisponiveisView` (JSON do modal) |
| `admin_prescricao_padrao.py` | registros no admin |
| `migrations/0002_*` | tabelas `admin_prescricoes_prescricaopadrao*` |

| Modelo | Papel |
|---|---|
| `PrescricaoPadrao` | cabeçalho: `descricao`, `observacao`, `profissional` **ou** `profissao`, `estabelecimento`, auditoria/status |
| `ProdutoPrescricaoPadrao` | item: espelha `ProdutoPrescricao` (`produto`, `intervalo_horas`, `hora_inicio_produto`, `se_necessario`, `dose_unica`, `observacao`) + `ordem` |
| `PrescricaoPadraoUtilizacao` | auditoria de uso (modelo × prescrição × atendimento × profissional) |

> A migração `admin_prescricoes.0002_*` depende de `prontuarios.0002` apenas porque a
auditoria referencia `prontuarios.Prescricao` (FK).

## Cadastro / gestão (admin)

`admin_prescricoes/admin_prescricao_padrao.py`, importado no fim de
`admin_prescricoes/admin.py`:

- **Prescrição Padrão**: lista (descrição, liberação, itens ativos, status) + inline
  `ProdutoPrescricaoPadraoInline` (produto, intervalo, horário, flags, ordem, status);
  no inline o campo `prescricao_padrao` é oculto (vem do objeto pai).
- **Produto da Prescrição Padrão**: cadastro avulso **com o campo
  `prescricao_padrao`** (obrigatório, só modelos ativos) — era o campo que faltava.
- **Utilização de Prescrição Padrão**: consulta apenas (`has_add/change = False`).

O queryset de produtos do inline usa o mesmo critério de `ProdutoPrescricaoForm`
(produto **ou** grupo marcado como “pode ser prescrito”, ativos).

## Arquivos

### Novos (todos em `admin_prescricoes/`)
| Arquivo | Conteúdo |
|---|---|
| `admin_prescricoes/models_prescricao_padrao.py` | modelos + `registrar_uso_prescricao_padrao()` |
| `admin_prescricoes/forms_prescricao_padrao.py` | `PrescricaoPadraoForm`, `ProdutoPrescricaoPadraoForm`, `ProdutoPrescricaoPadraoFormSet` |
| `admin_prescricoes/views_prescricao_padrao.py` | `PrescricoesPadraoDisponiveisView` (JSON do modal) |
| `admin_prescricoes/migrations/0002_prescricaopadrao_produtoprescricaopadrao_and_more.py` | tabelas do modelo/item/auditoria |
| `admin_prescricoes/admin_prescricao_padrao.py` | registros no admin |
| `templates/parciais/_prescricao_padrao_modal.html` | modal |
| `static/js/prescricao_padrao_modal.js` | carregamento, filtro, cards e inserção no formset |
| `static/css/prescricao_padrao.css` | estilo do botão da barra + correção de z-index do modal |

### Alterados (pontos mínimos, todos mapeados no rollback)
| Arquivo | Alteração |
|---|---|
| `prontuarios/urls.py` | rota `prescricoes_padrao_disponiveis` (importa a view de `admin_prescricoes`) |
| `prontuarios/views.py` | `PrescricaoCreateView`: `_limpar_itens_de_prescricao_padrao()` / `_registrar_uso_prescricao_padrao()` |
| `prontuarios/templates/prontuarios/prescricao_cadastrar.html` | barra “Assistente de Prescrição”, CSS, config JSON, include do modal e `<script>` |
| `admin_prescricoes/admin.py` | import do admin de prescrição padrão |
| `static/css/admin_forms_custom.css` | escopo do `.form-row` (ver correção de inline abaixo) |

## Correção — inline da Prescrição Padrão: produtos indevidos e linha vazia (20/10/2026)

### 1. Produtos não prescritíveis apareciam nas opções

O `autocomplete_fields` do Django consulta o **ModelAdmin de `Produto`**, ignorando
o queryset do form — por isso o select2 listava os 178 produtos, inclusive os
não prescritíveis.

**Correção** (`admin_estoques/admin.py::ProdutoAdmin.get_search_results`): quando a
consulta vem da Prescrição Padrão (referer contém `prescricaopadrao`), filtra:

```python
Q(pode_ser_prescrito=True) | Q(grupo__pode_ser_prescrito=True)
```

Validação: **80 de 178** produtos, **0 violações**. Outras telas que usam o
autocomplete de Produto continuam sem filtro (validado).

### 2. Linha final sem produto / não clicável

Três causas somadas:

| Causa | Correção |
|---|---|
| `extra = 1` criava uma linha vazia | `extra = 0` (itens entram por “Adicionar outro(a)…”) |
| `tr.form-row { display: revert }` (correção anterior) **vencia** o `.empty-form { display:none }` do jazzmin, exibindo o template | regra explícita `.empty-form { display:none !important }` |
| prefixo do formset `produtos` conflitava com `related_name` `Prescricao.produtos` | prefixo próprio + `verbose_name_plural` do inline |

### 3. Colunas cortadas / desalinhadas

Com `table-layout: fixed`, a coluna `original` (nome do item) ocupava 241px e as
colunas `status`/`DELETE` (ocultas no thead) ainda reservavam espaço no `tbody`,
deslocando th→td. Correções em `admin_forms_custom.css`:

- `td.original`, `td.field-status`, `td.delete` com `display: none` — usando
  `tr.form-row td.X` para vencer o `display: revert`;
- larguras explícitas por coluna (26% produto, 16% intervalo, 16% hora, 9% SN/DU,
  16% observação, 8% ordem — total 99%);
- labels das células ocultas no inline (o `<thead>` já nomeia as colunas);
- ícones `+`/lápis/×/olho ocultos no inline (roubavam a largura do select2);
- select2 compacto (34px) no inline.

**Verificado no navegador:** 2 linhas reais, nenhuma vazia, th e td com as mesmas
posições/larguras, `INTERVALOS`/`HORA DE INÍCIO` legíveis e tabela dentro do grupo.
Testes: `ProdutoPrescricaoPadraoAutocompleteTests` (2) + `PrescricaoPadraoTests` (4).

## Select2 de digitação no admin (20/10/2026)

Pedido: campos de localização por digitação (select2) no admin de prescrições, nos três pontos.

### Onde foi aplicado

| # | Tela | Campos com select2 |
|---|---|---|
| **1** | Admin → **Produto da Prescrição Padrão** (`add`/`change`) | `prescricao_padrao`, `produto`, `intervalo_horas`, `hora_inicio_produto` |
| **1b** | Inline dentro de **Prescrição Padrão** | `produto`, `intervalo_horas`, `hora_inicio_produto` |
| **2** | Admin → **Produto da Prescrição** (novo, `prontuarios.admin`) | `prescricao`, `produto`, `intervalo_horas`, `hora_inicio_produto` |
| **3** | **Prescrição** (`change`) | inline `ProdutoPrescricaoInline` somente leitura — o lançamento é feito na tela 2 |
| extra | Admin → **Prescrição Padrão** | `profissional`, `profissao`, `estabelecimento` |

Implementação com `autocomplete_fields` nativo do Django (o admin já usa select2
`admin-autocomplete`; todas as origens têm `search_fields`).

### Item 2 — admin que não existia

`prontuarios.admin.ProdutoPrescricaoAdmin` foi criado (`ProdutoPrescricao` não tinha
tela). `atendimento`/`estabelecimento` ficam fora do formulário porque
`ProdutoPrescricao.save()` os deriva da prescrição.

### Correções de CSS necessárias (admin custom)

O tema `admin_forms_custom.css` estiliza campos com `width/height` fixos, o que quebrou
o widget de autocomplete. Correções **escopadas**:

| Problema | Correção |
|---|---|
| `.form-row { display:flex }` atingia `<tr class="form-row">` dos inlines | escopo `fieldset .form-row:not(table *)` + `display: revert` nos `<tr>/<td>` |
| `select`/`input` com `height:48px` e `padding:12px 16px` espremiam o inline | regra compacta para `td` dos inlines |
| `.form-row > div { width:100% }` não pegava `.related-widget-wrapper.flex-container` | wrapper e `flex-container` com `width:100%` / `flex:1 1 100%` |
| `<select>` original (oculto) ocupava metade do wrapper no flex | `position:absolute; width:1px; flex:0 0 0` |
| `padding/height` do CSS custom vazava para o `<select>` interno do select2 | `select:not(.select2-hidden-accessible)` |
| `.select2-selection--single` com `display:flex` zerava a altura do texto | `display:block`, `height:46px`, `line-height:46px` no `__rendered` |
| select2 media largura antes do layout e gravava `width` inline pequeno | `static/js/admin_select2_largura.js` recalcula após o load (inclusive em `formset:added`) |

**Verificado no navegador real:** digitando `dipi` no select2 de *Produto* retornou
`Dipirona → Novalgina / Via Oral`; os 4 campos aparecem com largura cheia, seta e
ícones `+` / lápis do Django alinhados; console sem erros.

## Correção — campo `prescricao_padrao` ausente no admin (20/10/2026)

**Sintoma:** ao adicionar um *Produto da Prescrição Padrão* no admin não existia campo
para escolher a prescrição padrão.

**Causa:** o `ProdutoPrescricaoPadraoForm` listava em `Meta.fields` somente os campos do
produto — `prescricao_padrao` (FK obrigatória) estava de fora, então o Django não o
renderizava.

**Correção:** `prescricao_padrao` entrou em `Meta.fields` (obrigatório, queryset só com
modelos ativos). No inline da tela de *Prescrição Padrão* o campo continua oculto, pois o
vínculo vem do objeto pai (`ProdutoPrescricaoPadraoForm.inline_parent`, definido pela
subclasse criada em `ProdutoPrescricaoPadraoInline.get_formset`).

**Verificado no navegador:** o add exibe `Prescrição Padrão`, `Produto`, `Intervalos`,
`Hora de Início`; salvar um item completo grava com sucesso; o inline continua sem o campo.

## Correção — inline do admin com colunas espremidas (20/10/2026)

**Sintoma:** no change da *Prescrição Padrão*, a linha do inline aparecia com colunas de
~50px (produto/intervalo/hora espremidos).

**Causa:** `static/css/admin_forms_custom.css` tem `.admin-custom-change-form .form-row {
  display: flex; flex-direction: column; }` para o formulário vertical. Os inlines
tabulares do Django usam `<tr class="form-row">` — a regra transformava a linha num flex
container e os `<td>` viravam itens flex de largura mínima.

**Correção (escopo, sem reescrever o layout):**

```css
/* antes: .admin-custom-change-form .form-row { ... }              */
.admin-custom-change-form fieldset .form-row:not(table *),
.admin-custom-change-form div.form-row { /* layout vertical */ }

/* inlines voltam a ser tabela */
.admin-custom-change-form .inline-group table tr.form-row,
.admin-custom-change-form .inline-group table tr.form-row td { display: revert !important; }

/* widgets compactos no inline (o padding 12/16px não cabe em vTimeField) */
.admin-custom-change-form .inline-group table td input, … td select { height: 34px; padding: 4px 6px; }
```

> Esta alteração é **compartilhada**: corrige todos os inlines do admin do sistema (ex.:
> `ProfissionalEspecialidadeInline`). O backup original está em
> `.rollback/2026-10-20_prescricao_padrao/static/css/admin_forms_custom.css.bak` e é
> restaurado pelo rollback.

## Correção — modal escuro / não clicável (20/10/2026)

**Sintoma:** ao abrir o modal de prescrição padrão, ele aparecia escurecido e sem
resposta a cliques.

**Causa:** nesta tela também é carregado `static/css/evolucao_cadastrar_css.css`, que
resolve um problema antigo de stacking context no app de evolução com dois seletores
**globais/por ID**:

```css
/* estiliza QUALQUER backdrop, inclusive o de modais novos */
.modal-backdrop { z-index: 2147482000 !important; }

/* position/z-index altos só para estes três IDs */
.modal#modalTextosPadrao, .modal#modalDiagnosticos, .modal#modalDocumentoTextoPadrao {
    position: fixed !important; inset: 0 !important; z-index: 2147483000 !important;
}
```

Sem regra equivalente, `#modalPrescricaoPadrao` permanecia no `z-index: 1055` do
Bootstrap, **abaixo** do backdrop (2.147.482.000) — resultado: diálogo coberto pelo
overlay escuro, que ainda interceptava os cliques.

**Correção:** `static/css/prescricao_padrao.css` (arquivo exclusivo desta funcionalidade)
passa a estilizar o novo modal exatamente como os três já corrigidos:
`position: fixed` + `inset: 0` + `z-index: 2147483000` no `.modal`,
`2147483001` no `.modal-dialog` e `2147483002` no `.modal-content`, com
`pointer-events: auto` no diálogo, no conteúdo e nos elementos internos.

> Nenhum arquivo de evolução/documentos foi alterado — a correção fica isolada e sai
> junto com o rollback.

**Verificado no navegador (Playwright/patchright, usuário real logado):**

| verificação | resultado |
|---|---|
| modal abre pelo botão da barra | `#modalPrescricaoPadrao.show`, 1 backdrop |
| `z-index` / `position` | `2147483000` / `fixed` |
| `elementFromPoint` no centro do modal | elemento **dentro** do modal (não o backdrop) |
| background do `.modal-content` | `rgb(255, 255, 255)` |
| botão X clicável | fecha o modal, remove backdrop e o `modal-open` do body |
| clique em **Inserir** | item acrescentado ao formset (produto/intervalo/horário preenchidos, `item_padrao_id` presente) e toast exibido |
| console / requisições com erro | 0 / 0 |

## Verificação executada

- `python manage.py test prontuarios.tests.PrescricaoPadraoTests` → 4 testes OK
  (API filtra por liberação, API vazia sem parâmetros, renderização da barra/modal na
  tela, POST gravando item + auditoria).
- `python manage.py check` → 0 issues.
- `python manage.py makemigrations prontuarios` → 0003 e 0004 aplicadas.
- Renderização de `prescricao_cadastrar/3/` (200) contendo barra, botão, modal, JS, CSS
  e config JSON.
- `GET /prontuarios/prescricoes_padrao_disponiveis/` → JSON com o modelo liberado por
  profissão e seus itens.
- `POST prescricao_cadastrar/3/` com `produtos-0-item_padrao_id` → 302, prescrição e
  item gravados normalmente e `PrescricaoPadraoUtilizacao` criada.
- Dados de teste criados durante a validação foram removidos.

## Rollback

```bash
# restaura código e remove tabelas/migrações (com backup automático do db.sqlite3)
bash .rollback/2026-10-20_prescricao_padrao/rollback.sh

# apenas código, mantendo as tabelas (dados preservados)
bash .rollback/2026-10-20_prescricao_padrao/rollback.sh --só-codigo
```

O script:

1. restaura `prescricao_cadastrar.html`, `prontuarios/views.py`, `prontuarios/urls.py`,
   `admin_prescricoes/admin.py`, `prontuarios/models.py`, `prontuarios/forms.py`,
   `admin_prescricoes/models.py` e `static/css/admin_forms_custom.css` a partir dos `.bak`;
2. remove o hook de `prontuarios/apps.py` (se ainda existir de versão anterior);
3. apaga os arquivos novos em `admin_prescricoes/` (models/forms/views/admin/migração
   0002), o modal, JS e CSS — e também resíduos da versão que ficava em `prontuarios/`;
4. faz backup do `db.sqlite3`, executa `DROP TABLE` de
   `admin_prescricoes_prescricaopadrao{utilizacao,}` e
   `admin_prescricoes_produtoprescricaopadrao` (e das tabelas antigas de `prontuarios`,
   se existirem) e apaga os registros de migração correspondentes.

Validação do próprio rollback foi feita em uma cópia isolada do projeto: os arquivos
restaurados ficaram byte a byte iguais aos originais e `manage.py check` +
`makemigrations --check` não acusaram pendências.

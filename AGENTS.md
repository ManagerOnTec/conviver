# AGENTS.md

Regras por módulo. **Antes de mexer em um app, leia o `instrucoes_*.md` dele** —
ele manda mais que o código existente. Todos os admins seguem o padrão dos
demais (ver “Padrão obrigatório dos admins” abaixo).

| App | Instruções | Cobre |
|---|---|---|
| `admin_financeiro/` | `instrucoes_financeiro.md` | controle bancário, competências, movimentos, conciliação (OFX/PDF) |
| `admin_tesouraria/` | `instrucoes_tesouraria.md` | caixas, competências de caixa, movimentos de caixa, conferência |
| `admin_faturas/` | `instrucoes_faturas.md` | faturas, baixas, empacotamento, listagem editável |
| `admin_pagamentos/` | `instrucoes_pagamentos.md` | baixas de pagamento (banco **ou** caixa) |
| `admin_cadastros/` | `instrucoes_cadastros.md` | pessoas, empresas (`tipo`), estabelecimentos, barra de KPIs/filtros |
| `dominios/` | `instrucoes_dominios.md` | mixins, breadcrumbs, widgets, utils (vale para todos) |

> Se o app ainda não tem `instrucoes_*.md`, crie-o antes de implementar —
> modelo no fim deste arquivo.

## Padrão obrigatório dos admins (vale para todo ModelAdmin)

1. **Herança**: `AdminEstabelecimentoPadraoMixin` + `ExportToXLSMixin`
   (+ `StatusFilterAdminMixin` e `EstabelecimentoFilterAdminMixin` nos filtros).
2. **Breadcrumb**: automático via `dominios.breadcrumbs` — nunca escrever
   breadcrumb à mão em template. Telas próprias (não-ModelAdmin) usam
   `breadcrumbs_context(...)` + o include `admin/includes/breadcrumbs.html`.
3. **Menu**: ordem por `Meta.verbose_name_plural` = `"N. Nome"` (1, 2, 3…).
   Telas próprias entram por `_telas_extras` em `managerontec/admin_site.py`.
4. **Auditoria**: `us_registro`/`dt_registro` na criação e
   `us_atualizacao`/`dt_atualizacao` na alteração (no `save_model`).
5. **Estabelecimento**: nunca editável pelo usuário; vem da sessão/perfil.
6. **Mensagens**: sempre amigáveis, em português, dizendo **o que fazer**.
   Nunca deixar exceção/500 vazar para a tela: validações de admin capturam
   `ValidationError` e escrevem o erro na linha do formulário.
   - **sucesso → verde** (`#e7f6ec`, borda `#198754`)
   - **alerta → amarelo** (`#fff8e1`, borda `#e0a800`)
   - **perigo → vermelho** (`#fdecec`, borda `#dc3545`)

   `MESSAGE_TAGS` em `manage.py`/`settings.py` emite as classes do Django **e**
   as do Bootstrap (`error alert-danger`, `warning alert-warning`,
   `success alert-success`) — o admin pinta pelo `ul.messagelist li.{nivel}`
   (`admin_layout_toggles.css`, seção 7) e as páginas públicas pelo
   `includes/messagelist.html` (`msg-success`/`msg-warning`/`msg-error`).
7. **Período/competência**: nada grava em competência **FECHADA**; a data do
   lançamento tem de estar **dentro** do período da competência.
8. **Listagens editáveis**: usar `admin_faturas.changelist_editavel` (tabela
   montada no servidor, botão “Salvar” no canto superior direito).
9. **Filtros novos**: `SimpleListFilter` com `template` próprio
   (`admin/filter_multiselect.html` = múltipla escolha,
   `admin/filter_select2.html` = dropdown com busca) e **sempre** dentro de
   `try/except` — filtro inválido não pode derrubar a listagem.

   **9.a Estabelecimento do usuário (PADRÃO OBRIGATÓRIO).** Todo
   ModelAdmin cujo modelo **tenha o campo `estabelecimento`** inclui o
   `EstabelecimentoFilterAdminMixin` (`admin_cadastros/utils.py`) no
   `list_filter`:

   ```python
   from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
   list_filter = [..., EstabelecimentoFilterAdminMixin, ...]
   ```

   Ele filtra, **sem o usuário escolher nada**, pelo estabelecimento da
   **sessão** (`request.session['estabelecimento_id']`) e, sem sessão, pelo
   `estabelecimento_padrao` do perfil. Regras:

   - sessão **liberada** para o perfil → aplica o da sessão;
   - sessão **não liberada** → `PermissionDenied` (não cai em outro em
     silêncio);
   - usuário **sem perfil** (superuser puro) → não restringe;
   - escolha **manual** no filtro prevalece, limitada aos liberados;
   - gravação do valor: `AdminEstabelecimentoPadraoMixin` (fixa o campo no
     `get_form`, o usuário nunca troca).

   **Não use** o filtro em modelo **sem** o campo `estabelecimento`
   (ex.: `AcordoPagamento`, onde `estabelecimento` é `property` derivada do
   fornecedor): filtraria por um campo inexistente e a tela quebra com
   `FieldError`. Nesses casos o recorte é feito pelo **fornecedor/pagador**
   (`FornecedorPagadorFilter`).

10. **Telas listview do admin — layout obrigatório** (`admin_faturas/admin.py` e
    `admin_financeiro/admin.py` são a referência).

    Ordem na tela, de cima para baixo:
    1. **login/logout** (do `base_site.html`);
    2. **breadcrumb** padronizado (`admin/includes/breadcrumbs.html`);
    3. **dashboards** (KPIs) — `admin/includes/top_filter_and_kpis.html`;
    4. **filtros** (busca + barra analítica + filtros da direita);
    5. **ações** — **UMA** barra (`#admin-action-bar`) contendo, na **mesma
       linha**: `[◀ ▶]` + ações em lote + **Adicionar** e **Salvar** à direita.
       Não existe mais `object-tools` solto no topo nem segunda barra no
       rodapé;
    6. **tabela**.

    Regras de layout:
    - **Ocultar/exibir** cada sessão de topo (breadcrumb, indicadores, filtros)
      por botão próprio + barra de exibição + dock. **Indicadores e filtros
      começam RECOLHIDOS** (sem preferência salva), senão empurram a tabela
      para fora da tela. **Ações e tabela nunca são ocultadas.**
    - **Barra de ações e cabeçalho da tabela ficam fixos (`sticky`)** na
      rolagem; a tabela rola dentro do próprio quadro (`.results` com altura
      `clamp(320px, calc(100vh - 340px), 70vh)`), então o `<thead>` está
      sempre à vista.
    - **Rolagem horizontal acessível**: setas `◀ ▶` na barra de ações (acima
      da tabela), arrastar a tabela com o mouse e `Alt+←/→` — além da barra
      de rolagem nativa do rodapé. As células ficam em UMA linha
      (`white-space: nowrap`; só cliente/descrição quebram).
    - **Sem “Modo Foco/Zen”**: ele fazia o mesmo que o botão Breadcrumbs.
    - **Mensagens coloridas** (`ul.messagelist`, item 6): sucesso verde,
      alerta amarelo, perigo vermelho.
    - **Campo de TEXTO em `list_editable` não define a altura da linha**
      (`descricao`, `observacao`, `cliente`, `empenho`, `periodo_tratamento`…
      — lista em `ChangeListEditavel.campos_texto_longo`):
      - a célula mostra um **resumo em UMA linha** (até
        `limite_texto_celula` ≈ 60 caracteres) e um botão **“↗”**;
      - o `<textarea>` da listagem, quando houver, fica do **tamanho da row**
        (`height: 18px`, sem `resize`, sem quebra);
      - o botão abre o **MODAL de texto completo**
        (`modal-texto-overlay`, em `change_list_results_editavel.html`): texto
        integral em área somente leitura, **selecionável**, com botão
        **Copiar** (Clipboard API com fallback `execCommand`) e
        **Ctrl+C / Cmd+C**; fecha por Esc, pelo “✕”, pelo botão Fechar ou
        clicando fora.
      - a altura das linhas fica **uniforme** entre páginas (nenhuma linha
        estoura ao paginar). Estilo: `admin_layout_toggles.css`, seção 12.

    Implementação: `static/css/admin_layout_toggles.css` (seções 1-11),
    `static/js/admin_layout_toggles.js` (ocultar/exibir) e
    `static/js/admin_changelist_actions.js` (setas, arrastar, faixa de
    rolagem).


11. **Testes**: validar em transação com **rollback** (nenhum dado de teste
    persiste) e rodar `manage.py check` antes de concluir.

## Modelo de `instrucoes_<app>.md`

```markdown
# <App> — instruções

## Fluxo de negócio
1. ...
2. ...

## Regras obrigatórias (invariantes)
- ... (mensagem exata que o usuário deve ver)

## Menu e telas
- N. ...

## Validações
- ...

## Não fazer
- ...

## Como testar
- ...
```

## Padrão de PAGINAÇÃO e FILTROS do menul (listagens próprias — vale para
## todos os apps de tela própria, ex.: agenda_pacientes,
## gestao_tarefas_documentos, gestao_pessoas)

- **Paginação**: SEMPRE pelo `{% block paginate %}` do `base.html` com o
  painel `listing-pagination-panel` (copie o bloco de
  `agenda_pacientes/agenda_listar.html` — setas ◀ ▶, páginas −3/+3, meta
  "Exibindo X-Y de N registros", querystring preservada em todos os links).
  A listagem deve declarar `{% endblock %}` em `block lista` e fechar
  `block paginate` — nunca inventar outra paginação nem deixar sem.
- **Filtros do menul**: SEMPRE um **form crispy único** (`filter_form|crispy`)
  dentro do `<form method="GET">` do menul, com **Filtrar**/**Limpar** nos
  botões padrão do menu (`row mt-2` + `col-md-12` + `justify-content-center`,
  como na agenda). **NUNCA** montar filtros à mão com labels
  `form-label mb-0 small`, checkboxes `form-check ms-2 mb-1` soltos ou
  `mb-2` extras: ficam maiores que o padrão do sistema. Cada app cria o seu
  `*FiltroForm` (ex.: `FuncionarioFiltroForm`), inicializado com os filtros
  da sessão (`initial=filtros_sessao`).
- **Campos booleanos nos filtros do menul (checkbox/toggle)**: NUNCA usar
  `{{ filter_form|crispy }}` cru quando o form tem BooleanField — renderizar
  como o Atendimento (`atendimentos/atendimento_listar.html`), com o
  **toggle visual** (`filter-toggle-row` / `filter-toggle-label` /
  `filter-toggle-input` / `filter-toggle-track`, CSS global do base.html):

  ```django
  {% for field in filter_form %}
      {% if field.field.widget.input_type == 'checkbox' %}
          <div class="filter-toggle-row">
              <label class="filter-toggle-label" for="{{ field.id_for_label }}">{{ field.label }}</label>
              <span class="filter-toggle-control">
                  <input type="checkbox" name="{{ field.html_name }}"
                         id="{{ field.id_for_label }}" class="filter-toggle-input"
                         {% if field.value %}checked{% endif %}
                         {% if field.field.disabled %}disabled{% endif %}
                         aria-label="{{ field.label }}">
                  <span class="filter-toggle-track" aria-hidden="true"></span>
              </span>
          </div>
      {% else %}
          {{ field|as_crispy_field }}
      {% endif %}
  {% endfor %}
  ```

  Campos não-booleanos continuam `as_crispy_field`. `<form class="mt-2 ...">`
  (e não `mt-3`), igual ao atendimento.
- **Modais em listagens**: os `.modal.fade` devem ser movidos para o
  `<body>` no `DOMContentLoaded` (`document.body.appendChild(modal)`) —
  `#table-container` tem `z-index: 80` e modais dentro dele ficam ATRÁS do
  backdrop do Bootstrap (tela escurecida, nada clicável). Padrão da agenda.

## PADRÃO DE CRIAÇÃO — usuário logado + estabelecimento da sessão
## (todo CreateView de tela própria: agenda, gestão de tarefas/documentos,
## gestão de pessoas e próximos módulos)

- Todo objeto novo deve gravar, no `form_valid` da view:
  1. **usuário logado** no campo de auditoria de criação
     (`us_registro`/`usuario_cadastro` = `self.request.user`);
  2. **estabelecimento da SESSÃO**
     (`_estabelecimento(request)` lendo
     `request.session['estabelecimento_id']`) no campo `estabelecimento`
     — **nunca** oferecido como campo editável do formulário
     (`form.fields.pop('estabelecimento', None)` ou campo fora do form).
- Sem estabelecimento na sessão → recusar com mensagem amigável no form:
  *"Selecione o estabelecimento na barra superior antes de cadastrar…"*
  (nunca 500 e nunca criar órfão).
- Nas EDIÇÕES, gravar `us_atualizacao`/`usuario_atualizacao` +
  `dt_atualizacao` e **manter** o estabelecimento original (não regravar
  pelo form).
- O mesmo vale para o Admin: `AdminEstabelecimentoPadraoMixin` fixa o campo
  e o `save_model` grava o usuário (Padrão obrigatório dos admins, itens 4-5).

## PADRÃO DE SINTAXE HTML/TEMPLATE — tags {% %} nunca quebram em linhas
- Em templates, TODA tag `{% ... %}` (include, url, if, for, block...) deve
  ficar em **UMA ÚNICA LINHA**, mesmo que fique longa (a linha longa é aceita;
  a quebra NÃO é). Tag quebrada em várias linhas quebra a renderização —
  já quebrou `_list_header`, `_patient_context_header` e
  `_workflow_submit_sidebar` em vários módulos (o conteúdo some da tela sem
  erro no log).
- Regra do pep8/estilo Python NÃO se aplica a HTML/Django template: ignore
  o comprimento de linha do template; priorize a tag inteira na linha.
- Ao criar/atualizar um template, rode uma conferência de tags quebradas
  (regex `\{%[^%]*\n[^%]*?%\}`) antes de concluir.

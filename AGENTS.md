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
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
7. **Período/competência**: nada grava em competência **FECHADA**; a data do
   lançamento tem de estar **dentro** do período da competência.
8. **Listagens editáveis**: usar `admin_faturas.changelist_editavel` (tabela
   montada no servidor, botão “Salvar” no canto superior direito).
9. **Filtros novos**: `SimpleListFilter` com `template` próprio
   (`admin/filter_multiselect.html` = múltipla escolha,
   `admin/filter_select2.html` = dropdown com busca) e **sempre** dentro de
   `try/except` — filtro inválido não pode derrubar a listagem.
10. **Testes**: validar em transação com **rollback** (nenhum dado de teste
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
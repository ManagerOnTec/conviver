# admin_cadastros / gestao_leitos — instruções (base para o futuro app)

> **ESTE ARQUIVO É A ESPECIFICAÇÃO** para a criação futura do app
> **`gestao_leitos`** (gestão de ocupação de leitos por atendimento). Antes de
> implementar, ler também: `AGENTS.md` (padrão geral), as seções
> “PADRÃO DE PAGINAÇÃO e FILTROS do menul”, “PADRÃO DE CRIAÇÃO” e
> `agenda_pacientes/instrucoes_agenda_pacientes.md` e 'tarefa_listar.html' (padrão visual de referência).

## 1. Hierarquia existente (NÃO criar de novo)

A hierarquia física já existe em `admin_cadastros` e deve ser REUTILIZADA:

```
Estabelecimento → Ala (internacao?) → Setor → Local (online?) → Leito (ocupado?)

Novo objeto de registro de ocupacao sempre pega atendimento so estabelecimento logado, e pre carrega somente dados do estabelecimento logado na sessao.
```

- **Ala** (`Ala`): por estabelecimento; `internacao=True` libera leitos.
- **Setor** (`Setor`): da ala; valida mesmo estabelecimento.
- **Local** (`Local`): do setor (ou ONLINE sem setor, com `meio_online`/`link_online`);
  locais de ala de internação são os únicos que podem ter leitos.
- **Leito** (`Leito`): do local; `leito` único por local (`101-A`, `UTI-3`...);
  flag `ocupado` marcada pelo sistema; só existe em local de ala de internação.

O futuro app `gestao_leitos` **não duplica** nenhum desses cadastros: importa os
modelos de `admin_cadastros` (`from admin_cadastros.models import Leito, Local,
Setor, Ala`) e trabalha sobre eles + `Atendimento`.

## 2. Regra central: ATENDIMENTO ↔ LEITO

O vínculo é **atendimento → leito** (o paciente é sempre o do atendimento,
`atendimento.pessoa` — nunca um campo `pessoa` próprio):

```
GestaoLeito (registro de ocupação)
 ├─ leito            FK → admin_cadastros.Leito      (PROTECT)
 ├─ atendimento      FK → atendimentos.Atendimento   (PROTECT)
 ├─ dt_entrada       (default: agora) / dt_saida (null = ocupado)
 ├─ status           ('O' Ocupado, 'L' Livre, 'B' Bloqueado, 'H' Higienização)
 ├─ observacoes / us_registro / dt_registro / us_atualizacao / dt_atualizacao
 └─ estabelecimento  (herdado do leito; gravado pelo form da sessão)
```

**Invariantes obrigatórias:**
- **Um leito ativo por atendimento**: um atendimento só tem UMA ocupação ativa
  (constraint condicional `dt_saida__isnull=True`).
- **Um atendimento por leito**: leito com ocupação ativa só recebe um
  atendimento (constraint condicional no mesmo sentido).
- **Só leito de ala de internação**: recusar local de ala externa/online
  (*"O leito deve pertencer a um local de ala de internação."*).
- **Mesmo estabelecimento**: leito e atendimento devem pertencer ao
  estabelecimento da sessão (*"O atendimento não pertence ao estabelecimento
  selecionado."*).
- **Ocupação desencadeia flag**: ao gravar ocupação ativa, `leito.ocupado=True`;
  na saída/desocupação, `leito.ocupado=False` (e recalcula a listagem).
- **Alta do atendimento libera o leito**: quando `atendimento.dt_alta` é
  preenchido (tela de atendimento), o registro de ocupação ativo deve receber
  `dt_saida` (implementar hook/sinal ou verificação na listagem).
- **Inativar em vez de excluir**: registros com histórico nunca são apagados;
  desocupação é uma SAÍDA com data, não um delete.

**Permissões (mesmo padrão do restante do sistema):**
- `CustomPermissionRequiredMixin` + `FilterObjectsByEstabelecimentoMixin` nas
  views; permissões Django `view/add/change/delete_gestao` de leito.
- Liberação operacional opcional por estabelecimento
  (`ParametrosGestaoLeitos` no Admin: usuários OU grupos por
  `ver`/`editar`/`excluir`, superusuário sempre liberado, sem parâmetro →
  ninguém — copiar de `ParametrosAgenda`/`ParametrosGestaoDocumentos`).
- Card no `cadastros_index` exibido com
  `{% if user|has_perm:'gestao_leitos.view_gestao' %}`.

## 3. Tela principal — mapa de leitos (listagem)

Template `gestao_leitos/leito_mapa.html` seguindo o padrão da Agenda
(`base.html`; `menul` com **Novo** + filtros crispy + **Filtrar/Limpar**;
`cabdados` com `parciais/_list_header.html`; `block lista` com
`listing-table`; `{% block paginate %}` com `listing-pagination-panel`;
modais movidos para `<body>` via `document.body.appendChild` — ver AGENTS.md).

**Colunas:** Ações · Leito (código + local) · Setor · Ala · Estabelecimento ·
Paciente (nome do `atendimento.pessoa`, link para o atendimento) · Entrada ·
Dias internado · Situação · Status (badge colorido) · Observações.

**Filtros do menul (um único `LeitoMapaFiltroForm` crispy):**
- Busca (leito, paciente, CPF);
- Estabelecimento (da sessão);
- Ala / Setor / Local (dependentes, ativos);
- Situação: Ocupado · Livre · Bloqueado · Higienização · Todos;
- Status (A/I) como ÚLTIMO campo, antes de Filtrar/Limpar.

**Ações por linha (modais reais, POST):**
1. **Ocupar leito** (leito livre): modal escolhendo o atendimento (select2
   limitado aos atendimentos SEM alta e SEM ocupação ativa do estabelecimento)
   + data de entrada + observações;
2. **Registrar saída** (leito ocupado): modal com data de saída (padrão hoje)
   + motivo/alta — grava `dt_saida`, libera o leito, mantém o histórico;
3. **Trocar leito** (transferência): fecha a ocupação atual e abre nova no
   leito destino (TUDO em uma transação — nunca fica meio lançado);
4. **Bloquear/Desbloquear** e **Higienização**: mudança de status com motivo;
5. **Visualizar**: detalhe da ocupação (padrão detalhe: `_patient_context_header`,
   form de leitura com campos disabled, histórico);

**Nenhum botão sem backend; nenhum delete direto.**

## 4. Indicadores navegáveis (dashboard no topo)

Painel de KPIs clicáveis (mesmo padrão de `gestao_pessoas`/GTD) — cada card
filtra o mapa pelo próprio critério:

| Indicador | Cor | Filtro |
|---|---|---|
| Total de leitos ativos | azul | — |
| Ocupados | verde | `situacao=O` |
| Livres | azul-claro | `situacao=L` |
| Bloqueados | vermelho | `situacao=B` |
| Em higienização | laranja | `situacao=H` |
| Internados (pacientes do tipo PACIENTE) | roxo | atendimentos ativos no leito |
| Internados hoje (entradas do dia) | azul | `dt_entrada__date=hoje` |
| Altas hoje (saídas do dia) | verde | `dt_saida__date=hoje` |
| Taxa de ocupação (%) | amarelo | sem link (informativo) |

**Visual bonito/identificável:**
- Cards com contagem grande + rótulo + ícone (fa-hospital-user, fa-bed...);
- **Badges de situação nas linhas**: Ocupado `#198754`, Livre `#0dcaf0`,
  Bloqueado `#dc3545`, Higienização `#e0a800` (mesmo esquema de cores dos
  módulos financeiros/agenda);
- **Borda esquerda da linha** na cor da situação (padrão `border-left: 4px
  solid`, como na agenda);
- Pacientes destacados: nome em negrito + CPF pequeno, link para o
  **atendimento** (e daí para o prontuário).

## 5. Django Admin

Registrar em `gestao_leitos/admin.py` (padrão dos admins do AGENTS.md):
`AdminEstabelecimentoPadraoMixin` + `ExportToXLSMixin` +
`AdminDashboardAndTopFilterMixin` (KPIs + lookup de data do topo);
`list_display` com situação em badge colorido; `list_filter` com
`StatusFilterAdminMixin` + `EstabelecimentoFilterAdminMixin`; `search_fields`
(leito, local, paciente); inline do histórico; `save_model` gravando usuário
(`us_registro`/`us_atualizacao`) e `estabelecimento` herdado do leito.
Menu: `verbose_name_plural` com prefixo numérico ("1. Ocupações de Leitos",
"2. Parâmetros da Gestão de Leitos").

## 6. Fluxo de implementação (quando for criar)

1. `django-admin startapp gestao_leitos` + INSTALLED_APPS + URLs (`/leitos/`);
2. Models: `GestaoLeito` + `HistoricoLeito` (padrão GTD/GP: histórico nunca
   apagado) + `ParametrosGestaoLeitos`; constraints de unicidade condicional;
3. Forms: `LeitoMapaFiltroForm`, `OcuparLeitoForm`, `SaidaLeitoForm`,
   `TransferenciaLeitoForm`, `StatusLeitoForm` (extensões validadas);
4. Views (padrão agenda): `_estabelecimento(request)`, `_contexto_base`
   (`cad_index`, `list_index`, `estabelecimento`, `pode_ver/pode_editar/
   pode_excluir`), filtros em sessão (`leitos_filters`), modais por POST;
5. Templates: `leito_mapa.html` (listagem+KPIs+modais), `ocupacao_detalhe.html`,
   `ocupacao_form.html`; card no `cadastros_index`;
6. `instrucoes_gestao_leitos.md` no app, seguindo este arquivo;
7. Migrations; testes em transação com rollback (ocupar/desocupar/trocar,
   recusas de ala externa e estabelecimento divergente, alta liberando leito,
   históricos preservados) + `manage.py check`.

## Não fazer

- Não duplicar Ala/Setor/Local/Leito: reutilizar `admin_cadastros`.
- Não criar campo `pessoa` no vínculo: o paciente é o do atendimento.
- Não permitir leito em local de ala não-internação (a validação do model
  `Leito` já recusa; a view deve dar mensagem amigável, nunca 500).
- Não deixar o mapa sem paginação padrão nem filtros à mão (AGENTS.md).
- Não apagar ocupações: saída = `dt_saida` + histórico.

# agenda_pacientes — instruções
## Fluxo de negócio
- Agendar eventos por **atendimento** e por tipo de agenda.
- **O agendamento é por ATENDIMENTO** (`AgendaPaciente.atendimento`). Não existe
  campo `pessoa` no agendamento: o paciente é **sempre** o do atendimento
  (`agenda.atendimento.pessoa`). Nada de duplicidade atendimento/paciente.
- **Tipo configurado para exigir exame → vinculado ao EXAME SOLICITADO**
  (`AgendaPaciente.exame` → `prontuarios.Exame`). A dependência é controlada
  por `TipoAgendamento.exige_exame_solicitado`, não pelo texto da descrição.
- **Cadastros auxiliares da agenda ficam em `admin_cadastros`**:
  Alas, Setores, Locais e Leitos. A hierarquia é
  **Estabelecimento → Ala → Setor → Local → Leito**. A Ala define se os
  locais do setor são de internação; o tipo de agendamento define se o
  atendimento é interno ou externo.
- Neste app ficam apenas: `1. Parâmetros da Agenda`, `2. Tipos de Agendamento`,
  `3. Agendas de Pacientes`. A agenda em si é operada por **templates
  próprios** (`/agenda/agenda_listar/` etc.).

## Regras obrigatórias
- O tipo de agenda deve ser informado.
  - Mensagem: **"Informe o tipo de agendamento."**
  - Tipo inativo não pode ser usado: **"Este tipo de agendamento está inativo.
    Selecione um tipo ativo."**
- A criação pela agenda completa pré-seleciona um tipo compatível, quando
  disponível. Na lista de exames, o modal de agendamento oferece os tipos
  ativos configurados para exigir exame solicitado.
- Sempre que for agenda do tipo exame exibir tambem na lista do pedido de exame o agendamento.
  - `prontuarios.exames_views.ExameListView` vincula os agendamentos ativos
    ao exame solicitado correspondente. A lista mostra data e local na linha
    de cada exame; clicar abre o detalhe em modal.
  - Endpoint JSON `agendaexame_lista` (`/agenda/agenda_exame/<atendimento>/`)
    continua disponível para o cabeçalho do prontuário.
- Na lista de exames, **Agendar** abre um modal na própria linha; atendimento,
  paciente, exame solicitado e dados da solicitação já vêm carregados. A
  listagem não oferece edição de agenda. Cada exame pode ter apenas um
  agendamento ativo; para alterar um existente, use a tela própria da agenda.
- O modal de resultado só permite registro depois que o agendamento ativo
  estiver marcado como efetuado. Registrar o resultado não altera essa
  situação; a validação é aplicada também no servidor/modelo.
- Liberacao por admin agenda — **por usuário OU por grupo**
  - `ParametrosAgenda` (menu admin **"1. Parâmetros da Agenda"**) por
    estabelecimento: `usuarios_visualizacao`/`grupos_visualizacao`,
    `usuarios_edicao`/`grupos_edicao`, `usuarios_exclusao`/`grupos_exclusao`,
    `status`.
  - `ParametrosAgenda.pode(usuario, estabelecimento, acao)` é a única fonte:
    libera se o usuário está em **usuários OU em qualquer grupo** da ação
    (superusuário sempre pode; sem parâmetro ativo → **ninguém** pode).
- Cadastros auxiliares via admin, agenda em si via template proprio.
  - Locais da agenda vêm de `admin_cadastros.Local` (ligado ao `Setor`, que
    tem o `estabelecimento`); `TipoAgendamento.local` é o local sugerido.
  - Telas: `agenda_listar.html`, `agenda_cadastrar.html`,
    `agenda_editar.html` (ambos estendem `agenda_form.html`) e
    `agenda_detalhe.html`.
- Ter a liberacao da url com a devida permissao ou negacao de acesso no cadastros_index.
  - `cadastros_index.html` mostra o card só com
    `has_perm:'agenda_pacientes.view_agendapaciente'`.
  - Nas views, `LiberacaoAgendaMixin` (`acao_agenda` = `ver`/`editar`/`excluir`)
    exige **permissão Django + liberação no admin**: sem liberação o usuário vê
    a mensagem de alerta e volta para o `cadastros_index` (nunca 500 nem
    página branca). `agendaexame_lista` responde `403` com JSON vazio.
  - Permissões usadas: `view_agendapaciente`, `add_agendapaciente`,
    `change_agendapaciente`, `delete_agendapaciente`.
- sempre analisar o get context data, cad_index, list_index, title, titulo e outros, mais estes sao fundamentos para os templates que vem do template base.
  - `_contexto_base()` entrega `titulo`, `title`, `func`, `estabelecimento`,
    `cad_index`, `list_index`, `menu_agenda`, `pode_ver`, `pode_editar`,
    `pode_excluir`.
  - A listagem ainda entrega `agendas` (context_object_name),
    `tipos_agendamento`, `agenda_filters` (filtros da sessão em
    `request.session['agenda_filters']`), `filter`, `querystring`,
    `is_paginated`, `today`.
- manter padrao, nav, menul, cabdados, tabela, paginacao, botoes de filtro, limpeza, salvar, menul com botoes padroes de voltar, listar, etc (semelhate ao app prontuarios e modelos relacionados em menul, quando tiver )
  - Listagem: menu lateral com **Novo**, filtros
    (busca/tipo/efetuado/data inicial/data final) + **Filtrar** e **Limpar**;
    **Download** abaixo dos filtros exporta em CSV os mesmos registros
    filtrados da listagem;
    cabeçalho `parciais/_list_header.html`; tabela `listing-table` com
    `listing-action-bar` (ver/editar/efetuar/excluir conforme liberação);
    editar, detalhe e excluir são ações exclusivas da listagem; exclusão
    acontece por POST após confirmação JavaScript, sem tela intermediária;
    paginação preservando a querystring dos filtros.
  - Formulário: menu lateral voltar/lista, `crispy` nos campos e
    `parciais/_workflow_submit_sidebar.html` para salvar.
  - `/agenda/agenda_listar/?limpar=1` limpa os filtros (inclusive da sessão).

## Menu e telas
- Admin **agenda_pacientes**: `1. Parâmetros da Agenda`,
  `2. Tipos de Agendamento`, `3. Agendas de Pacientes`.
- Admin **admin_cadastros**: `9. Estabelecimentos`, `10. Setores`,
  `11. Locais`, `12. Leitos` (cadastros auxiliares da agenda/leitos).
- Sistema: card **Agenda de Pacientes** no `cadastros_index` →
  `/agenda/agenda_listar/`.

## Validações — AGENDA ↔ EXAME (regra central)
- **Sempre validar o TIPO**: sem tipo → *"Informe o tipo de agendamento."*;
  tipo inativo → *"Este tipo de agendamento está inativo. Selecione um tipo
  ativo."*
- **Tipo de EXAME exige EXAME SOLICITADO** (`AgendaPaciente.exame`):
  - se `TipoAgendamento.exige_exame_solicitado` estiver ativo e faltar exame →
    *"Para este tipo de agendamento, selecione o exame solicitado do
    atendimento."*
  - o exame **deve pertencer ao atendimento setado** → *"Este exame não
    pertence ao atendimento informado."*
  - o exame **não pode ter sido executado** (sem resultado) → *"Este exame já
    foi executado e não pode ser agendado novamente."*
  - tipo NÃO-exame com exame setado → *"Somente agendamento do tipo exame
    pode estar vinculado a um exame."*
- **Execução espelhada**: efetuar/desfazer na agenda marca/desmarca o
  `ResultadoExame` do exame (e vice-versa quando aplicável) — o que faz em um
  reflete no outro (`AgendaPaciente.efetuar()` e
  `AgendaPaciente.sincronizar_execucao()`). Registrar resultado pelo modal da
  lista de exames, por si só, **não** conclui o agendamento.
- Local online exige link: **"Este local é online: informe o link da
  videochamada ou do WhatsApp."**
- Sem estabelecimento na sessão: **"Selecione o estabelecimento na barra
  superior antes de cadastrar uma agenda."**
- Exclusão apenas pela ação da listagem, com confirmação JavaScript.
- `AgendaPacienteForm.clean()` **deve retornar `dados`** — o
  `super().clean()` é quem carrega `_post_clean` (validação do modelo).

## Não fazer
- Não expor resultados inativos na listagem ou no download.
  - Listagem e download: `queryset.filter(status='A')`.
  - Admin: sem filtro escolhido, o `ChangeList` já abre filtrando `status='A'`.
- Não seguir breadcrumb/menul à mão fora do padrão do `base.html`.
- Não colocar lógica de permissão fora de `ParametrosAgenda.pode()`.

## Como testar
- `python manage.py check` e `makemigrations --check` (sem migração pendente).
- Sem liberação em `ParametrosAgenda`: `/agenda/agenda_listar/` volta ao
  `cadastros_index` com alerta amarelo.
- Com liberação `editar`: cadastrar agenda com tipo ativo (sucesso verde),
  sem tipo (mensagem na linha do campo), com tipo inativo (mensagem na linha
  do campo).
- Marcar/desmarcar “efetuado” pela listagem e conferir `dt_efetuado`.
- `?limpar=1` e paginação preservam/limpam os filtros corretamente.
- Na lista de exames do atendimento, agenda de tipo exame aparece no painel
  superior e o link abre a agenda já com o atendimento.
- Validar em transação com **rollback** (nenhum dado de teste persiste).

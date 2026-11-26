# gestao_tarefas_documentos — instruções

Gestão de Tarefas e Documentos: documentos institucionais (CRM, COREN,
alvarás, licenças, POP...) com **vigência/renovação/validação** e **tarefas**
ligadas opcionalmente a um documento. Segue o padrão da **Agenda de
Pacientes** e o Padrão obrigatório dos admins do AGENTS.md.

## Fluxo de negócio

1. **Tipo** — tipo de documento (cadastrado pelo usuário, NADA fixo em código).
2. **Documento** — tipo + anexo (PDF/JPG/JPEG/PNG/DOC/DOCX/XLS/XLSX, ≤ 5 MB,
   validador `FileExtensionValidator` + `validate_anexo_file`) + vigências.
3. **Situação do documento** — **calculada pelas datas** (nunca por status
   manual):
   - `vigente` (verde): `vigencia_final >= hoje` e sem renovação aberta;
   - `proximo` (amarelo): vence em até `dias_proximo_vencimento` (padrão 30,
     configurável por estabelecimento em `ParametrosGestaoDocumentos`);
   - `vencido` (vermelho): `vigencia_final < hoje`;
   - `aguardando_renovacao` (azul): `inicio_renovacao <= hoje`;
   - `sem_vigencia` (cinza): sem `vigencia_final` ou inativo.
4. **Tarefa** — providência vinculada (ou não) a um documento: pendente →
   em andamento → concluída/cancelada; **atrasada** = prazo vencido e não
   concluída/cancelada (destaque vermelho).

## Regras obrigatórias (invariantes)

- **Liberação**: `ParametrosGestaoDocumentos.pode(usuario, estabelecimento,
  acao)` é a ÚNICA fonte (`ver`/`editar`/`excluir`); usuários OU grupos;
  superusuário sempre pode; sem parâmetro ativo → **ninguém**. Sem liberação,
  a view volta ao `cadastros_index` com alerta amarelo (nunca 500).
- **Validação**: registra usuário + data/hora + histórico. Desvalidar
  **exige justificativa** e a validação anterior fica preservada no histórico.
- **Renovação**: novas vigências + início da próxima renovação + anexo
  opcional (extensões validadas); tudo no histórico.
- **Anotação**: nova anotação é **acrescentada** às anteriores (nunca sobrescreve).
- **Histórico** (`HistoricoDocumento`/`HistoricoTarefa`): cadastro, alteração,
  validação, desvalidação, renovação, substituição de anexo, anotação e
  mudança de situação — **nunca é apagado**.
- **Exclusão**: não há exclusão definitiva — documento/tarefa são
  **inativados/cancelados** com histórico mantido.
- Contexto dos templates: `cad_index`, `list_index`, `estabelecimento`,
  `pode_ver`/`pode_editar`/`pode_excluir`, `querystring`, `filter`,
  `is_paginated`, `today` (mesmos nomes da agenda).

## Menu e telas

- Admin: `1. Tipos de Documento` · `2. Documentos` · `3. Tarefas` ·
  `4. Histórico de Documentos` · `5. Histórico de Tarefas` ·
  `6. Parâmetros da Gestão de Documentos`.
- Sistema: card **Gestão de Tarefas e Documentos** no `cadastros_index`
  (exibe com `view_documento`) → `/gtd/documento_listar/`; tarefas em
  `/gtd/tarefa_listar/`.
- Listagem de documentos: filtros (busca, tipo, situação, vigência final
  de/até) + **Filtrar**/**Limpar** (filtros em sessão `gtd_documento_filters`);
  KPIs clicáveis no topo; ações por linha: Visualizar, Editar, Validar/
  Desvalidar, Renovar, Anotar, Inativar (modais Bootstrap, POST real).
- Listagem de tarefas: filtros (busca, documento, situação — inclui
  **Atrasadas** —, prioridade); ações: Iniciar, Concluir, Reabrir, Cancelar,
  Anotação, Editar, Cancelar/Inativar.

## Validações

- Tipo sem descrição ou duplicado ativo → erro no campo.
- `vigencia_final < vigencia_inicial` → erro; `inicio_renovacao >
  vigencia_final` → erro (form e model).
- Anexo fora da lista de extensões → *"Extensão não permitida..."*.
- Tarefa sem título → erro; prazo antes da criação → erro; conclusão fixa
  `data_conclusao = hoje` quando status = C.
- Sem estabelecimento na sessão → *"Selecione o estabelecimento na barra
  superior..."*.

## Não fazer

- Não fixar tipos de documento em código.
- Não excluir documento/tarefa (inativar/cancelar).
- Não apagar linhas de histórico.
- Não sobrescrever anotações antigas.
- Não filtrar a situação por campo gravado: é **calculada**.

## Como testar

`python manage.py check` e, em `with transaction.atomic():` + rollback:
1. criar tipo duplicado ativo → recusado;
2. documento com vigência final < inicial → recusado;
3. anexo `.exe` → recusado;
4. `situacao` calculada: vigente/amarelo/vencido/aguardando/sem vigência;
5. validar → histórico e `dt_validacao`; desvalidar sem motivo → recusado,
   com motivo → `validado=False` e histórico preserva a validação anterior;
6. renovar (novas datas + anexo) → histórico;
7. anotação preserva as anteriores;
8. tarefa: iniciar → em andamento → concluir (data de conclusão) → reabrir →
   cancelar; atrasada com prazo vencido;
9. sem `ParametrosGestaoDocumentos` → `/gtd/documento_listar/` volta ao
   `cadastros_index` com alerta;
10. KPIs clicáveis filtram a listagem.

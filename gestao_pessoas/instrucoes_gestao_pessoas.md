# gestao_pessoas — instruções

Gestão de Pessoas: os **funcionários são PESSOAS já cadastradas**
(classificação `funcionario` em `Pessoa.classificacao_pessoa`) — o módulo
acrescenta a relação funcional, **sem duplicar** nome/CPF/telefone. Segue o
padrão da Agenda de Pacientes e o Padrão obrigatório dos admins do AGENTS.md.

## Fluxo de negócio

```
Pessoa (classificação "funcionario") → Funcionario → Documentos, ASO, Ficha,
Cartão-Ponto, Exames Periódicos, Cursos (CursoFuncionario ← Curso) e Férias.
```

- **Funcionario** — `pessoa` (OneToOne), `data_admissao`,
  `status_funcionario` (ativo/afastado/desligado), anotações, auditoria.
  Recusa pessoa sem a classificação FUNCIONÁRIO e admissão futura.
- **Documentos do funcionário** — tipo, anexo (PDF/JPG/JPEG/PNG/DOC/DOCX/
  XLS/XLSX ≤ 5 MB), data do documento; anexar não apaga os anteriores.
- **ASO** — tipos: admissional, periódico, retorno ao trabalho, mudança de
  riscos, demissional; agendamento → realização → validade → anexo.
  **Agendar cria um ASO NOVO — o histórico nunca é apagado.**
- **Ficha de registro** — anexo + data; substituir cria NOVA linha
  (versão anterior preservada).
- **Cartão-ponto** — número único entre cartões ativos.
- **Exame periódico** — controle independente dos demais ASOs, com data do
  próximo exame e histórico consultável.
- **Cursos** — `Curso` cadastrável (NR-32, NR-10, brigada...; nada fixo em
  código); `CursoFuncionario` (realizado/pendente/vencido) calcula validade a
  partir de `validade_meses` do curso; vencido = validade < hoje.
- **Férias** — período aquisitivo/concessivo, dias de direito × gozados
  (**não pode ultrapassar o saldo**), férias integrais/fracionadas; alertas de
  concessivo vencendo (≤ 30 dias) e vencido.

## Tela principal (`/gp/funcionario_listar/`)

Colunas: Ações · Funcionário · Admissão · **Documentos** (anexar/ver/qtde) ·
**ASO** (situação+datas/agendar/registrar/histórico) · **Ficha de Registro**
(cadastrada/pendente + anexar/ver) · **Cartão-Ponto** (nº/pendente/editar) ·
**Periódico** (situação/agendar/registrar/histórico) · **Cursos Obrigatórios**
(ok/pendentes/vencidos + administrar) · **Férias** (aquisitivo, saldo,
próximas + registrar/programar/início/retorno/histórico) · Situação.

- Todas as operações em **modais** com POST real (nada só visual); após salvar
  a listagem volta atualizada.
- **Dashboard clicável**: funcionários ativos · sem ficha · ASO não agendado ·
  ASO agendado · periódico pendente · cursos vencidos · cursos pendentes ·
  férias próximas do limite — cada KPI abre a listagem já filtrada.
- **Filtros combináveis**: nome/CPF, situação, admissão (de/até), sem ASO,
  ficha pendente, periódico pendente, cursos vencidos, férias pendentes
  (sessão `gp_filters`; `?limpar=1` limpa).

## Regras obrigatórias (invariantes)

- **Liberação**: `ParametrosGestaoPessoas.pode(usuario, estabelecimento,
  acao)` é a ÚNICA fonte (ver/editar/excluir; usuários OU grupos;
  superusuário sempre; sem parâmetro → ninguém). Sem liberação, volta ao
  `cadastros_index` com alerta amarelo.
- **Histórico** (`HistoricoFuncionario`): cadastro, alteração, documentos,
  ASO (agendamento/realização), ficha, cartão, periódico, cursos, férias e
  mudança de situação — **nunca é apagado**.
- Validações: ASO/periódico agendado exige data; realização ≥ agendamento;
  curso realizado exige data; dias gozados ≤ dias de direito; datas finais
  ≥ iniciais; anexos só nas extensões permitidas.
- Contexto dos templates: `cad_index`, `list_index`, `estabelecimento`,
  `pode_ver`/`pode_editar`/`pode_excluir`, `querystring`, `filter`,
  `is_paginated`, `today`.

## Menu e telas

- Admin: `1. Funcionários` · `2. Documentos do Funcionário` · `3. ASOs` ·
  `4. Fichas de Registro` · `5. Cartões-Ponto` · `6. Exames Periódicos` ·
  `7. Cursos Obrigatórios` (+ Cursos do Funcionário) · Férias ·
  `8. Histórico de Funcionários` · `9. Parâmetros da Gestão de Pessoas`.
- Sistema: card **Gestão de Pessoas** no `cadastros_index` (exibe com
  `view_funcionario`) → `/gp/funcionario_listar/`.

## Validações

- Pessoa sem classificação funcionário → *"A pessoa precisa estar
  classificada como FUNCIONÁRIO no cadastro de Pessoas."*
- Sem estabelecimento na sessão → *"Selecione o estabelecimento na barra
  superior..."* (views de cadastro).
- Anexo fora da lista → *"Extensão não permitida..."*.
- Cartão-ponto duplicado ativo → recusado.
- Férias gozadas > direito → recusado (form e model e no registrar retorno).

## Não fazer

- Não duplicar dados pessoais (moram em `Pessoa`).
- Não apagar histórico, ASOs anteriores ou versões de ficha.
- Não fixar cursos/tipos em código.
- Não criar botões sem backend.

## Como testar

`python manage.py check` e, em `with transaction.atomic():` + rollback:
1. funcionário com pessoa não-funcionária → recusado;
2. anexo .exe → recusado;
3. ASO: agendar (novo registro) → registrar realização → histórico
   preservado; cancelar;
4. ficha: anexar → substituir (nova linha, anterior preservada);
5. cartão duplicado → recusado;
6. periódico: agendar → registrar com próximo exame;
7. curso: marcar pendente → registrar realizado (validade calculada) →
   vencido quando validade < hoje;
8. férias: aquisitivo → programar → iniciar → retorno (saldo não pode
   estourar); concessivo vencendo gera alerta;
9. telas 200 com superusuário (KPIs, modais renderizando);
10. sem `ParametrosGestaoPessoas` → `/gp/funcionario_listar/` volta ao
    `cadastros_index` com alerta.

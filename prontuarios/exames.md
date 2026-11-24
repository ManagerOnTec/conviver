# Prontuários — módulo de Exames
## Objetivo
Implementar no prontuário um fluxo de solicitação e registro de resultados de exames, integrado à navegação clínica, ao admin de permissões e à geração de relatórios assináveis.

## Fluxo de negócio
1. Um administrador cadastra os `TipoExame` e libera os tipos para um estabelecimento, profissão ou profissional em `ParametrosExames` (`admin_exames`).
2. No atendimento, o profissional autorizado cria uma solicitação (`Exame`) com tipo e solicitação/indicação obrigatória, anexo/laudo opcional e opção de assinatura.
3. O exame pode ter vários registros de `ResultadoExame`, cada um com data, anotações e até três anexos.
4. O cadastro inicial não exibe campos de resultado; na edição, resultados existentes podem ser corrigidos e novos resultados registrados. A inativação do resultado é feita pelo campo de status, sem exclusão física pela tela pública.
5. O sistema cria PDF pelo fluxo de prontuário (`salvar_pdf_prontuario`), respeitando o gerenciador personalizado por tipo de exame e, na ausência dele, o gerenciador geral do estabelecimento. A assinatura utiliza o certificado do perfil, como nos demais relatórios.

## Regras e decisões
- Na edição do exame, o campo Status permite ativar ou inativar a solicitação.
  O cadastro inicial mantém o status oculto com o padrão ativo.
- O tipo selecionável no formulário é a interseção das liberações ativas do profissional (ou da profissão ativa) com o estabelecimento da sessão.
- O tipo padrão da liberação é usado como seleção inicial quando pertence aos tipos liberados.
- O exame usa o estabelecimento do atendimento; o formulário não permite trocar esse vínculo.
- Os anexos do resultado aceitam `.pdf`, `.png`, `.jpg` e `.jpeg`, com o validador de tamanho do projeto (5 MB por arquivo). Há três campos de arquivo por resultado.
- Resultados inativos não são apresentados na listagem do prontuário.
- A lista de Exames tem filtros no menu lateral no padrão da Evolução: ID, tipo de exame, data de registro, data do resultado, usuário/data de criação e atualização e status. A data do resultado considera apenas resultados ativos; por padrão, a lista mostra exames ativos.
- Os filtros aplicados são preservados na sessão do atendimento e o botão “Limpar” os remove e retorna ao status padrão (ativo).
- Cada linha mostra data e local do agendamento ativo do exame; o detalhe da agenda abre em modal. “Agendar” abre um modal na própria linha com paciente, atendimento, exame e solicitação carregados. A lista não permite editar agendamento, e cada exame admite apenas um agendamento ativo.
- A anotação da agenda é obrigatória no modal de agendamento.
- Ao registrar resultado pela lista, data e anotação são obrigatórias. Na tela
  de edição do exame, os formulários de resultado são opcionais; os resultados
  existentes podem ser corrigidos e novos resultados podem ser adicionados.
- A tabela apresenta, após as ações, tipo, solicitação/indicação em modal, profissional solicitante, data da solicitação, agendamento, status do agendamento (não agendado, não efetuado ou efetuado), resultado e profissional que registrou o resultado. Datas de resultados existentes abrem o modal com anotações e links protegidos para os anexos correspondentes.
- O modal de resultado só fica disponível após o agendamento ativo ser
  marcado como efetuado. O servidor e o modelo também bloqueiam o registro sem
  essa condição; lançar o resultado não altera a situação do agendamento.
- Os anexos são servidos por uma view autenticada, com verificação de permissão e estabelecimento; não se expõe diretamente a URL do storage.
- Anotações e anexos dos resultados não aparecem mais em colunas da listagem; ficam no modal de detalhe do resultado. O anexo da solicitação continua disponível no detalhe do exame.
- As rotas de exame são separadas em `prontuarios/exames_views.py`, mas incluídas em `prontuarios/urls.py`, para evitar dependência circular com o módulo legado e preservar seu funcionamento.
- A tela administrativa de Exames é estatística/somente leitura; edição clínica ocorre nas telas do prontuário. A exclusão clínica é feita pela inativação do status, não há exclusão física na tela pública.

## Arquivos principais
- Modelos: `prontuarios/models.py` (`Exame`, `ResultadoExame`) e `admin_exames/models.py` (`TipoExame`, `ParametrosExames`).
- Administração de tipos/liberações: `admin_exames/admin.py`.
- Telas e formulários: `prontuarios/exames_views.py`, `prontuarios/forms_exames.py`, `prontuarios/exames.py`.
- Templates: `prontuarios/templates/prontuarios/exame_{listar,cadastrar,detalhe,editar}.html`.
- Relatórios: `prontuarios/relatorios.py` e escolha/gerenciador de relatórios em `dominios/choices.py` e `admin_relatorios`.
- Migrações: `admin_exames/migrations/0001_initial.py`, `0002_tipoexame_cor_iniciais.py`; `prontuarios/migrations/0003_exames.py`; migrations subsequentes em `admin_relatorios/migrations`.

## Como testar
- `python manage.py check`.
- Aplicar migrations em banco de teste e testar permissão por estabelecimento/profissão/profissional.
- Testar upload de PDF, PNG, JPG e JPEG e rejeição de extensão não permitida/tamanho superior ao limite.
- Testar cadastro e alteração de exame e múltiplos resultados; confirmar auditoria, links autenticados dos anexos e relatório/assinatura conforme certificado configurado.
- Testar na lista de exames o agendamento por linha, o modal de detalhe, a rejeição de um segundo agendamento ativo para o mesmo exame e o registro de resultado sem concluir a agenda.
- Testar os estados da coluna Resultado, o modal com anotações e anexos, e o acesso autenticado a cada anexo.
- Rodar os testes `prontuarios.tests.ExamesProntuarioTests` em banco de teste transacional. Não usar dados reais.

## Estado e limitações conhecidas
- Implementados modelos, permissões, admin, rotas, listagem, cadastro, edição, detalhe, anexos protegidos e integração inicial com relatório assinado.
- Migrations `admin_exames` e `prontuarios` aplicadas ao banco SQLite padrão do projeto; as tabelas `prontuarios_exame` e `prontuarios_resultadoexame` foram confirmadas. Se a aplicação estiver conectada a outro banco/arquivo SQLite, também será necessário aplicar as migrations nesse banco.
- A migration `admin_relatorios/0008_exame_personalizado_relatorio.py` adiciona o vínculo por tipo de exame. `0009` é apenas migration de encadeamento, `0010` adiciona a escolha do relatório e `0011` foi criada como migration final do campo; conferir e remover operações redundantes antes de aplicar se o histórico de migrations for reorganizado.
- O valor máximo de resultados por exame não é restrito globalmente; cada resultado aceita no máximo três anexos. Se o negócio exigir quantidade máxima de resultados, falta definir esse limite.
- A suíte completa de testes ainda precisa ser executada, assim como um teste de ponta a ponta de geração/assinatura PDF no ambiente com certificado/storage configurado.
- A visualização ampliada das anotações usa o `title` nativo do navegador, não um modal customizado.
- O template de edição deve ser conferido após POST inválido para garantir que erros de cada formulário inline apareçam junto ao respectivo resultado.

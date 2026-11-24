# prontuarios — instruções
## Fluxo de negócio
- A listagem de prontuários (`/prontuarios/prontuario_listar/`) usa `AtendimentoFilter` do app atendimentos e mantém filtros na sessão.
- `dt_alta` é o booleano de inclusão/exclusão de atendimentos com alta.

## Regras obrigatórias
- Booleanos no menu lateral da listagem devem usar o switch acessível comum do `templates/base.html` (`filter-toggle-row`, `filter-toggle-input`, `filter-toggle-track`), igual à listagem de Atendimentos.
- Prontuário deriva de Atendimento. Para exibir o acordo associado use `form.acordo_faturamento`; não existe `form.convenio`.
- Manter nomes/valores GET, persistência de filtros, método queryset e label dos filtros.
- O switch é checkbox nativo com label associado, acessível via teclado e submetido como checkbox.

## Não fazer
- Não duplicar a implementação CSS do switch em prontuários; reutilizar as classes globais.
- Não alterar lógica do `AtendimentoFilter` só para estilo.

## Exames
- A navegação do prontuário deve listar Exames imediatamente abaixo de Evoluções em todas as telas clínicas, preservando o atendimento atual.
- Tipos disponíveis vêm de `admin_exames.ParametrosExames` ativos por estabelecimento, profissão ou profissional. O tipo padrão deve estar entre os liberados.
- Solicitação / Indicação do exame é obrigatória e não pode conter apenas espaços.
- Na edição do exame, o próprio campo Status é exibido para permitir ativar
  ou inativar o exame. No cadastro inicial, o status permanece oculto e ativo.
- A listagem de exames apresenta, nesta ordem, tipo, solicitação/indicação em modal, profissional solicitante, data da solicitação, agendamento, status do agendamento, resultado e profissional que registrou o resultado. Anotações completas e anexos protegidos ficam no modal de resultado; cada resultado aceita até três anexos PDF/PNG/JPG/JPEG (5 MB por arquivo).
- A listagem de Exames mantém filtros de ID, tipo, datas de registro/resultado, usuário/data de auditoria e status na sessão; “Limpar” remove os filtros salvos e mantém o status ativo padrão.
- Cada linha de exame mostra o agendamento ativo com data e local. O detalhe abre em modal; “Agendar” abre um modal na própria linha com paciente, atendimento, exame e solicitação carregados. A lista não permite editar agendamento, e só pode existir um agendamento ativo por exame.
- A anotação da agenda é obrigatória no modal de agendamento.
- Resultado registrado pela lista exige data e anotação. Na tela de edição do
  exame, os campos dos resultados existentes podem ser mantidos ou corrigidos
  sem tornar o resultado inteiro obrigatório em novos formulários vazios.
- O modal de resultado só fica disponível após o agendamento ativo ser marcado
  como efetuado. Registrar o resultado não altera a situação do agendamento.
- O PDF do exame usa os gerenciadores de relatório e a assinatura digital existentes.
- Especificação, estado, testes e limitações estão em `prontuarios/exames.md`.

## Como testar
- Abrir `/prontuarios/prontuario_listar/`, alternar o filtro de alta e confirmar que a requisição filtra como antes.
- Testar fluxo de Exames conforme `prontuarios/exames.md`.
- `manage.py check`.

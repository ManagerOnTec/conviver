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

## Como testar
- Abrir `/prontuarios/prontuario_listar/`, alternar o filtro de alta e confirmar que a requisição filtra como antes.
- `manage.py check`.

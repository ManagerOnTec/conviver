# atendimentos — instruções
## Fluxo de negócio
- A listagem pública autenticada de atendimentos (`/atendimentos/atendimento_listar/`) filtra registros pelo estabelecimento permitido e mantém filtros na sessão para paginação.
- Os filtros são gerados por `AtendimentoFilter` (`atendimentos/views.py`) e renderizados no menu lateral com crispy forms.

## Regras obrigatórias (invariantes)
- Melhorias visuais nos filtros não podem mudar nomes de parâmetros, valores ou comportamento de `AtendimentoFilter`.
- Booleanos devem manter semântica nativa acessível: label associado, foco por teclado, estado marcado/desmarcado e submissão como checkbox.
- O toggle deve funcionar em telas pequenas e não esticar o checkbox à largura inteira do menu.

## Menu e telas
- `/atendimentos/atendimento_listar/` — listagem e filtros de atendimentos.
- Cadastro, edição e detalhe renderizam o campo `Atendimento.acordo_faturamento` usando `form.acordo_faturamento`; não existe `form.convenio`.

## Validações
- `dt_alta` continua filtrando registros com/sem alta conforme os valores BooleanFilter.
- Filtros de não booleanos e ações da listagem permanecem inalterados.

## Não fazer
- Não substituir o BooleanFilter por parâmetros manuais nem alterar a lógica do queryset.
- Não aplicar o visual de switch indiscriminadamente a botões, radios ou checkboxes fora do formulário de filtros.

## Como testar
- Abrir a listagem de atendimentos e verificar visual, alinhamento, foco e alternância do filtro `dt_alta`.
- Executar `manage.py check`.

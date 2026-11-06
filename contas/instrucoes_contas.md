# contas — instruções
## Fluxo de negócio
- `User` possui no máximo um `Perfil`, editado como inline no admin do usuário.
- O Perfil associa um funcionário e os estabelecimentos liberados; o estabelecimento padrão deve pertencer à lista de estabelecimentos liberados.
- No cadastro/edição do Perfil, o administrador de implantação precisa conseguir pesquisar e selecionar estabelecimentos sem depender de estabelecimento já escolhido na sessão.

## Regras obrigatórias (invariantes)
- Os campos de pessoa e estabelecimento do Perfil exibem somente registros ativos; pessoa deve ter classificação `funcionario`.
- Estabelecimento padrão deve estar entre os estabelecimentos liberados.
- O autocomplete deve permitir busca nos campos relacionados e nunca depender do `AdminEstabelecimentoPadraoMixin` para o inline de Perfil.
- O Perfil é gerenciado pelo inline de Usuário; qualquer `ModelAdmin` de Perfil usado para validar o autocomplete não deve aparecer no menu.

## Menu e telas
- `1. Grupos` e `2. Usuários`; Perfil é um inline do usuário e não uma tela/menu separado.

## Validações
- Mensagens de validação devem permanecer no formulário, sem erro 500.
- O endpoint de autocomplete do Perfil deve aceitar os campos `pessoa`, `estabelecimento` e `estabelecimento_padrao`, com resultados ativos apenas.

## Não fazer
- Não aplicar `AdminEstabelecimentoPadraoMixin` ao inline de Perfil: o fluxo configura os estabelecimentos liberados, antes de qualquer estabelecimento de sessão estar selecionado.
- Não depender de `HTTP_REFERER` para decidir se a busca ajax filtra inativos quando o endpoint é identificável diretamente.

## Como testar
- `manage.py check`.
- Abrir `/admin/auth/user/<id>/change/` sem estabelecimento na sessão e confirmar que o autocomplete de estabelecimentos pesquisa e retorna apenas ativos.
- Testar `/admin/autocomplete/` com `app_label=contas`, `model_name=perfil`, `field_name=estabelecimento` e confirmar resposta HTTP 200.

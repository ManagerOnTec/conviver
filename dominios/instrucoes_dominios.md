# dominios — instruções

## Fluxo de negócio

`dominios` fornece mixins, widgets e utilitários compartilhados pelos apps.
Mudanças em helpers compartilhados devem manter o comportamento dos
consumidores existentes; novos comportamentos precisam ser opt-in.

O seletor de campo de data do filtro superior é habilitado com
`dashboard_date_filter_fields = '__all__'`; sem essa configuração, o
consumidor mantém seu campo de data padrão.

## Regras obrigatórias

- Não alterar o comportamento padrão de `ExportToXLSMixin` para os outros
  admins.
- Exportações com anexos devem oferecer planilha e arquivos correspondentes
  juntos, com links relativos válidos dentro do pacote extraído.
- Falhas ao ler um anexo devem ser informadas ao usuário; não retornar uma
  exportação parcial com aparência de sucesso.
- Seguir as instruções de `AGENTS.md` e os padrões de auditoria/permissão dos
  admins consumidores.

## Menu e telas

- Não há telas ou itens de menu próprios.

## Validações

- Consumidores que habilitam o seletor superior de data devem oferecer cada
  campo `DateField`/`DateTimeField` local do modelo; `DateTimeField` usa
  comparação por data para incluir o dia inteiro.
- Validar que as exportações mantêm todos os registros selecionados.
- Validar que cada link da planilha aponta ao arquivo correspondente no ZIP.
- Executar testes direcionados e `manage.py check`.

## Não fazer

- Não habilitar o empacotamento de anexos para todos os modelos sem opt-in.
- Não usar caminhos absolutos ou URLs do armazenamento original como links
  para documentos que acompanham a exportação.
- Não ocultar falhas de leitura dos anexos nem entregar pacotes incompletos.

## Como testar

- Testar exportação sem anexos e preservar o XLSX existente.
- Testar exportação com múltiplos campos/anexos, confirmar o conteúdo do ZIP e
  resolver cada hyperlink relativo para o membro correspondente.

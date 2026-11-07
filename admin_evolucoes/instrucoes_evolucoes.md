# admin_evolucoes — instruções
## Fluxo de negócio
- Tipos de evolução e textos padrão são cadastrados no admin e selecionados no formulário de evolução clínica (`prontuarios`).
- A inserção de texto padrão deve preservar o HTML rico cadastrado, inclusive parágrafos, ênfase, listas, quebras e espaços relevantes, permitindo edição posterior no TinyMCE.

## Regras obrigatórias
- A API JSON dos textos entrega o conteúdo sem achatá-lo em texto puro.
- O cliente insere o HTML rico diretamente no editor TinyMCE; não passar o conteúdo completo por `textContent`/`strip_tags`.
- Se TinyMCE não estiver disponível, converter blocos para texto mantendo quebras de linha (não concatenar parágrafos).

## Não fazer
- Não normalizar todo o texto com `\s+`, `trim()` ou conversão para `textContent` antes de inserir no editor.
- Não sobrescrever o documento atual; inserir no cursor ou início conforme a ação existente.

## Como testar
- Inserir texto padrão com parágrafos, espaços, lista e negrito e confirmar que o editor mantém a formatação e que ainda é editável.
- `manage.py check`.

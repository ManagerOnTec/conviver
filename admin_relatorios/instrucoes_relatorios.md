# admin_relatorios — instruções
## Fluxo de negócio
- Textos padrão são cadastrados no admin e inseridos em atas, ofícios e orçamentos pelas telas públicas de documentos.
- A inserção deve preservar HTML rico, quebras de parágrafo, listas, ênfases e espaçamento relevante, mantendo o texto editável no TinyMCE.

## Regras obrigatórias
- O endpoint de texto padrão retorna o valor original de `TextoDocumentoPadrao.texto` sem achatá-lo.
- O JavaScript insere HTML rico diretamente no TinyMCE e salva o conteúdo no textarea/form.
- Fallback para textarea deve preservar quebras entre blocos e não concatenar palavras.

## Não fazer
- Não converter o HTML completo para `textContent` para a inserção no editor.
- Não usar `trim()` nem substituir todas as sequências de whitespace no conteúdo inserido.
- Não alterar endpoint/modelo em incompatibilidade de tipo de documento sem necessidade.

## Como testar
- Inserir um modelo com parágrafos, lista, espaços e negrito em Ata, Ofício e Orçamento; conferir aparência, edição e valor enviado no formulário.
- `manage.py check`.

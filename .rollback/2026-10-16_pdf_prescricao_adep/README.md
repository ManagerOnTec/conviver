# Melhoria do PDF de prescrição e ADEP — 16/10/2026

## Problemas corrigidos

### 1. Tabela passava por cima do campo de assinatura digital
A tabela de prescrição/ADEP era montada como uma **`Table` única com uma
sub-tabela aninhada numa célula**. O ReportLab **não divide tabelas
aninhadas** entre páginas; como consequência, quando havia muitos itens a
tabela invadia a faixa reservada à assinatura (ou o rodapé), em vez de gerar
novas páginas.

**Correção:** `admin_relatorios/rel_paragrafos.py` agora devolve uma **lista de
flowables** para `tipo in {'prescricao', 'adep'}`. Cada bloco de linhas é uma
`Table` independente com `repeatRows=1`, permitindo ao loop de paginação em
`prontuarios/relatorios.py` dividir o conteúdo entre páginas naturalmente e
repetir o cabeçalho em cada página. O espaço reservado à assinatura
(`signature_bottom=62`, `signature_height=50`) passa a ser respeitado.

### 2. Colunas desalinhadas e dados "desconfigurados"
- O separador interno do produto era `:` (ex.: `Dipirona:mg:O`), o que ficava
  ilegível.
- O split global por `<br/>` em `genParagrafosRel` **quebrava a linha do
  produto no meio**, gerando linhas desalinhadas.
- A linha de produto sem ADEP tinha **5 colunas**, enquanto o cabeçalho tinha
  6 — desalinhando a tabela.

**Correção:**
- Coluna 1 (produto) concentra descrição + unidade + via, com `<br/>` interno
  (pode estourar em várias linhas).
- Demais colunas (intervalo, SN, dose, observações, administrado) permanecem
  **em linha única**.
- Prescrição/ADEP são tratados **antes** do split global por `<br/>`, então o
  separador de linhas da tabela é o fim de linha (`\n`) e o `<br/>` fica
  restrito ao interior da célula.
- Ambas as ramificações (com e sem ADEP) agora emitem **6 colunas**
  consistentes com o cabeçalho.

### 3. HTML no campo de parágrafo (similar ao modelo de evolução)
As células da tabela agora são interpretadas como HTML pelo `Paragraph`,
aceitando marcações simples como `<b>`, `<i>`, `<u>` e `<br/>`. O
`limpar_html_para_pdf` preserva essas tags.

## Arquivos alterados
- `admin_relatorios/rel_paragrafos.py`
  - nova função `_build_tabela_prescricao_adep`
  - `genParagrafosRel` desvia prescrição/adep antes do split global
- `prontuarios/relatorios.py`
  - montagem das linhas de produto (coluna única + `<br/>`)
  - cabeçalho e linhas sempre com 6 colunas
- `prontuarios/tests.py`
  - nova classe `PrescricaoAdepPdfTests` (6 testes)

## Testes
`python manage.py test prontuarios.tests.PrescricaoAdepPdfTests`

Cobrem: lista de flowables pagináveis, coluna de produto com quebra, demais
colunas em linha, HTML simples e quebra real em múltiplas páginas.

> Observação: existem 3 testes pré-existentes em
> `EvolucaoValidationAndPdfTests` que já falhavam antes desta mudança
> (`test_pdf_adds_dedicated_photo_page_for_ata_attachment`,
> `test_pdf_adds_dedicated_photo_page_for_orcamento_attachment`,
> `test_pdf_keeps_single_long_paragraph_from_first_page_to_last`). Não foram
> introduzidos por esta melhoria.

## Rollback
Executar:

```bash
bash .rollback/2026-10-16_pdf_prescricao_adep/rollback.sh
```

Isso restaura os arquivos originais a partir dos `.bak` guardados em
`.rollback/2026-10-16_pdf_prescricao_adep/`.

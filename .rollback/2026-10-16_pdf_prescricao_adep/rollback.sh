#!/usr/bin/env bash
# Rollback do trabalho "PDF de prescrição e ADEP" (16/10/2026).
#
# Restaura os arquivos originais guardados em .rollback/2026-10-16_pdf_prescricao_adep/
# Uso:
#   bash .rollback/2026-10-16_pdf_prescricao_adep/rollback.sh
#
# O script NÃO mexe em banco de dados nem em migrações: as alterações deste
# trabalho são apenas de geração de PDF (layout/colunas) e de código Python.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SNAP_DIR="$ROOT_DIR/.rollback/2026-10-16_pdf_prescricao_adep"

declare -A ARQUIVOS=(
  ["prontuarios/relatorios.py"]="relatorios.py.bak"
  ["admin_relatorios/rel_paragrafos.py"]="rel_paragrafos.py.bak"
  ["prontuarios/utils.py"]="utils.py.bak"
  ["prontuarios/tests.py"]="tests.py.bak"
)

for destino in "${!ARQUIVOS[@]}"; do
  origem="$SNAP_DIR/${ARQUIVOS[$destino]}"
  if [[ ! -f "$origem" ]]; then
    echo "AVISO: backup não encontrado: $origem" >&2
    continue
  fi
  cp "$origem" "$ROOT_DIR/$destino"
  echo "Restaurado: $destino"
done

echo "Rollback concluído."

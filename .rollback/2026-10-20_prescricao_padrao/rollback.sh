#!/usr/bin/env bash
# Rollback do trabalho "Prescrição Padrão / Assistente de Prescrição" (20/10/2026).
#
# Restaura:
#   - prontuarios/templates/prontuarios/prescricao_cadastrar.html (template original)
#   - prontuarios/views.py, prontuarios/urls.py (hooks mínimos)
#   - admin_prescricoes/admin.py (import do admin de prescrição padrão)
#
# Remove:
#   - arquivos NOVOS criados somente para esta funcionalidade
#   - migrações 0003 e 0004 de prontuarios
#   - tabelas prontuarios_prescricaopadrao / prontuarios_produtoprescricaopadrao /
#     prontuarios_prescricaopadraoutilizacao (DROP TABLE, se existirem)
#
# Uso:
#   bash .rollback/2026-10-20_prescricao_padrao/rollback.sh            # restaura código + remove tabelas
#   bash .rollback/2026-10-20_prescricao_padrao/rollback.sh --só-codigo # restaura código, mantém tabelas
#
# ATENÇÃO: o DROP TABLE é destrutivo — apague antes os modelos de prescrição padrão
#          que você queira preservar (exportar) ou rode com --só-codigo.

set -euo pipefail

# Interpretador Python: usa o mesmo do ambiente virtual do projeto, se existir
# (o `python` do PATH pode não ter Django instalado).
PYTHON_BIN="python"
for candidato in "$(dirname "${BASH_SOURCE[0]}")/../../.venv/bin/python" \
                 "$(dirname "${BASH_SOURCE[0]}")/../../venv/bin/python"; do
  if [[ -x "$candidato" ]]; then
    PYTHON_BIN="$candidato"
    break
  fi
done

SOMENTE_CODIGO=0
if [[ "${1:-}" == "--só-codigo" || "${1:-}" == "--so-codigo" ]]; then
  SOMENTE_CODIGO=1
fi

if [[ -n "${BASH_SOURCE[0]}" ]]; then
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
else
  ROOT_DIR="/home/resid/projetos_managerontec/conviver"
fi
SNAP_DIR="$ROOT_DIR/.rollback/2026-10-20_prescricao_padrao"

echo "==> Restaurando arquivos alterados"
declare -A ARQUIVOS=(
  ["prontuarios/templates/prontuarios/prescricao_cadastrar.html"]="prontuarios/templates/prontuarios/prescricao_cadastrar.html.bak"
  ["prontuarios/views.py"]="prontuarios/views.py.bak"
  ["prontuarios/urls.py"]="prontuarios/urls.py.bak"
  ["admin_prescricoes/admin.py"]="admin_prescricoes/admin.py.bak"
  ["prontuarios/models.py"]="prontuarios/models.py.bak"
  ["prontuarios/forms.py"]="prontuarios/forms.py.bak"
  ["admin_prescricoes/models.py"]="admin_prescricoes/models.py.bak"
  ["prontuarios/admin.py"]="prontuarios/admin.py.bak"
  ["admin_estoques/admin.py"]="admin_estoques/admin.py.bak"
  ["static/css/admin_forms_custom.css"]="static/css/admin_forms_custom.css.bak"
)

for destino in "${!ARQUIVOS[@]}"; do
  origem="$SNAP_DIR/${ARQUIVOS[$destino]}"
  if [[ ! -f "$origem" ]]; then
    echo "AVISO: backup não encontrado: $origem" >&2
    continue
  fi
  cp "$origem" "$ROOT_DIR/$destino"
  echo "  Restaurado: $destino"
done

echo "==> Removendo hook de apps.py"
APPS_PY="$ROOT_DIR/prontuarios/apps.py"
if [[ -f "$APPS_PY" ]] && grep -q "models_prescricao_padrao" "$APPS_PY"; then
  "$PYTHON_BIN" - "$APPS_PY" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path, encoding='utf-8').read()
novo = re.sub(
    r"\n[ \t]*# Modelos de PRESCRIÇÃO PADRÃO.*?"
    r"from prontuarios import models_prescricao_padrao[^\n]*\n",
    "\n",
    src,
    count=1,
    flags=re.S,
)
if novo == src:
    print("  AVISO: trecho de prescrição padrão não encontrado em apps.py (verifique manualmente)")
else:
    open(path, 'w', encoding='utf-8').write(novo)
    print("  Limpo: prontuarios/apps.py")
PY
fi

echo "==> Removendo arquivos criados por esta funcionalidade"
ARQUIVOS_NOVOS=(
  "admin_prescricoes/models_prescricao_padrao.py"
  "admin_prescricoes/forms_prescricao_padrao.py"
  "admin_prescricoes/views_prescricao_padrao.py"
  "admin_prescricoes/admin_prescricao_padrao.py"
  "admin_prescricoes/migrations/0002_prescricaopadrao_produtoprescricaopadrao_and_more.py"
  "admin_prescricoes/migrations/0003_alter_prescricaopadrao_options.py"
  # resíduos da versão anterior (modelos ficavam em prontuarios)
  "prontuarios/models_prescricao_padrao.py"
  "prontuarios/forms_prescricao_padrao.py"
  "prontuarios/views_prescricao_padrao.py"
  "prontuarios/migrations/0003_prescricaopadrao_produtoprescricaopadrao.py"
  "prontuarios/migrations/0004_prescricaopadraoutilizacao_and_more.py"
  "templates/parciais/_prescricao_padrao_modal.html"
  "static/js/prescricao_padrao_modal.js"
  "static/js/admin_select2_largura.js"
  "static/css/prescricao_padrao.css"
)
for rel in "${ARQUIVOS_NOVOS[@]}"; do
  if [[ -f "$ROOT_DIR/$rel" ]]; then
    rm "$ROOT_DIR/$rel"
    echo "  Removido: $rel"
  fi
done
find "$ROOT_DIR/prontuarios/__pycache__" "$ROOT_DIR/admin_prescricoes/__pycache__" \
  -name '*prescricao_padrao*' -delete 2>/dev/null || true
find "$ROOT_DIR/admin_prescricoes/migrations/__pycache__" \
  -name '0002_prescricaopadrao*' -o -name '0003_alter_prescricaopadrao*' -delete 2>/dev/null || true
find "$ROOT_DIR/prontuarios/migrations/__pycache__" \
  -name '0003_prescricaopadrao*' -o -name '0004_prescricaopadraoutilizacao*' -delete 2>/dev/null || true

if [[ "$SOMENTE_CODIGO" -eq 0 ]]; then
  echo "==> Removendo tabelas e registros de migração do banco"
  DB_FILE="$ROOT_DIR/db.sqlite3"
  if [[ -f "$DB_FILE" ]]; then
    BKP="$DB_FILE.bak-rollback-prescricao-padrao-$(date +%Y%m%d-%H%M%S)"
    cp "$DB_FILE" "$BKP"
    echo "  Backup do banco: $BKP"
  fi
  # Feito via Django (não depende do cliente sqlite3 instalado)
  MANAGE_PY="$ROOT_DIR/manage.py"
  ( cd "$ROOT_DIR" && "$PYTHON_BIN" "$MANAGE_PY" shell 2>/dev/null <<'PY'
from django.db import connection

tabelas = [
    'admin_prescricoes_prescricaopadraoutilizacao',
    'admin_prescricoes_produtoprescricaopadrao',
    'admin_prescricoes_prescricaopadrao',
    # resíduos da versão anterior (modelos ficavam em prontuarios)
    'prontuarios_prescricaopadraoutilizacao',
    'prontuarios_produtoprescricaopadrao',
    'prontuarios_prescricaopadrao',
]
with connection.cursor() as cur:
    for tabela in tabelas:
        cur.execute('DROP TABLE IF EXISTS ' + tabela)
        print('  DROP TABLE', tabela)
    cur.execute(
        "DELETE FROM django_migrations WHERE app = 'admin_prescricoes' "
        "AND name IN ('0002_prescricaopadrao_produtoprescricaopadrao_and_more', "
        "'0003_alter_prescricaopadrao_options')"
    )
    cur.execute(
        "DELETE FROM django_migrations WHERE app = 'prontuarios' "
        "AND name IN ('0003_prescricaopadrao_produtoprescricaopadrao', "
        "'0004_prescricaopadraoutilizacao_and_more')"
    )
    print('  registros de migração removidos:', cur.rowcount)
PY
  )
else
  echo "==> Tabelas do banco mantidas (--só-codigo)."
  echo "    Para removê-las depois: bash .rollback/2026-10-20_prescricao_padrao/rollback.sh"
fi

echo
echo "Rollback concluído. Recomenda-se rodar: python manage.py check"

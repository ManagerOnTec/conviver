/**
 * ============================================================================
 * ADMIN CHANGELIST — BARRA DE AÇÕES EM CIMA *E* EMBAIXO DA LISTAGEM
 * ============================================================================
 * O template (templates/admin/change_list.html) renderiza duas barras de ação:
 *
 *   [ações] [tabela] [ações] [paginação]
 *
 * A tabela de `list_editable` é montada no servidor pelo ChangeListEditavel
 * (admin_faturas/changelist_editavel.py). Este script só cuida da posição:
 * se a 1ª barra tiver ficado abaixo da tabela, recoloca-a acima.
 */
(function () {
  'use strict';

  function posicionarBarraDeAcoes() {
    var form = document.getElementById('changelist-form');
    if (!form) return;

    var tabela = form.querySelector('#result_list') || form.querySelector('table');
    var barras = form.querySelectorAll('.actions');
    if (!tabela || barras.length < 2) return;

    var primeira = barras[0];
    if (primeira.compareDocumentPosition(tabela) & Node.DOCUMENT_POSITION_FOLLOWING) {
      return; // já está acima
    }
    var destino = tabela.closest('.results') || tabela;
    destino.parentNode.insertBefore(primeira, destino);
    primeira.classList.add('actions-top');
  }

  function iniciar() {
    posicionarBarraDeAcoes();
    setTimeout(posicionarBarraDeAcoes, 150);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

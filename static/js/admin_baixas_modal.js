/*
 * MODAL DE BAIXAS DA FATURA
 *
 * O botão "Baixas (n)" da listagem abre `/admin/admin_faturas/fatura/<pk>/baixas/`
 * numa janela modal em vez de navegar. O conteúdo é a própria tela do servidor
 * (resumo + tabela + formulário), carregada por `fetch` — assim o saldo e a
 * soma das baixas vêm sempre recalculados.
 *
 * Fecha por Esc, pelo "✕" ou clicando fora.
 */
(function () {
  'use strict';

  var overlay = null;
  // Algo mudou dentro do modal (baixa lançada/excluída)? Ao fechar,
  // recarrega a LISTAGEM para atualizar o saldo e o contador "Baixas (n)".
  var houveAlteracao = false;

  /**
   * Recarrega a changelist MANTENDO os filtros.
   *
   * `location.reload()` preserva a query string inteira (busca, período,
   * atalhos, dropdowns e paginação), então os filtros continuam aplicados —
   * só zeram pelo botão “✕ Limpar Todos os Filtros”.
   */
  function recarregarListagem() {
    window.location.reload();
  }

  /**
   * Garante o CSS do modal e o do conteúdo das baixas.
   *
   * O conteúdo chega por `fetch` e é injetado como `innerHTML`: o
   * `{% block extrastyle %}` do template NÃO é carregado nesse caminho —
   * por isso o estilo mora em ARQUIVO e é injetado aqui, uma vez.
   */
  function carregarEstilos() {
    if (document.getElementById('baixas-modal-css')) return;
    var base = (window.STATIC_URL || '/static/').replace(/\/?$/, '/');
    [base + 'css/admin_layout_toggles.css',
     base + 'css/admin_baixas_modal.css'].forEach(function (href) {
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      document.head.appendChild(link);
    });
    var marcador = document.createElement('meta');
    marcador.id = 'baixas-modal-css';
    document.head.appendChild(marcador);
  }

  function criarOverlay() {
    if (overlay) return overlay;
    carregarEstilos();
    overlay = document.createElement('div');
    overlay.className = 'baixas-modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.innerHTML =
      '<div class="baixas-modal-box">' +
      '  <div class="baixas-modal-header">' +
      '    <span class="baixas-modal-titulo">Gestão de baixas</span>' +
      '    <button type="button" class="baixas-modal-fechar"' +
      '            title="Fechar (Esc)" aria-label="Fechar">✕</button>' +
      '  </div>' +
      '  <div class="baixas-modal-corpo"></div>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.baixas-modal-fechar')
      .addEventListener('click', fechar);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) fechar();
    });
    return overlay;
  }

  function fechar() {
    if (overlay) overlay.style.display = 'none';
    if (houveAlteracao) {
      houveAlteracao = false;
      recarregarListagem();
    }
  }

  function extrairConteudo(html) {
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var wrap = doc.querySelector('.baixas-wrap');
    if (!wrap) return null;
    // Clona SÓ o miolo do `.baixas-wrap` (sem o <style> e sem o chrome do
    // admin que vem em volta no HTML completo da página).
    var clone = wrap.cloneNode(true);
    // As mensagens do Django ficam no nível da página: recolhe e põe aqui
    // dentro para que apareçam no modal.
    var msgs = doc.querySelectorAll('ul.messagelist li, .baixas-msg');
    if (msgs.length && !clone.querySelector('.baixas-mensagens')) {
      var box = doc.createElement('div');
      box.className = 'baixas-mensagens';
      msgs.forEach(function (m) {
        var d = doc.createElement('div');
        d.className = 'baixas-msg ' + (m.className || '');
        d.textContent = m.textContent.trim();
        box.appendChild(d);
      });
      clone.insertBefore(box, clone.firstChild);
    }
    return clone.innerHTML;
  }

  function abrir(url) {
    var el = criarOverlay();
    var corpo = el.querySelector('.baixas-modal-corpo');
    corpo.innerHTML = '<p style="padding:20px">Carregando…</p>';
    el.style.display = 'flex';

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var conteudo = extrairConteudo(html);
        if (conteudo === null) {
          corpo.innerHTML = '<p style="padding:20px;color:#b91c1c">' +
            'Não foi possível localizar o conteúdo das baixas.</p>';
          return;
        }
        corpo.innerHTML = conteudo;
        ligarFormularios(corpo, url);
      })
      .catch(function () {
        corpo.innerHTML =
          '<p style="padding:20px;color:#b91c1c">' +
          'Não foi possível carregar as baixas.</p>';
      });
  }

  /**
   * Envia os formulários do modal por `fetch` e TROCA o conteúdo pelo
   * resultado — a página da listagem não navega. Assim as mensagens de
   * sucesso/erro e o resumo recalculado aparecem dentro do próprio modal.
   */
  function ligarFormularios(corpo, url) {
    corpo.querySelectorAll('form').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (form.dataset.confirmar &&
            !window.confirm(form.dataset.confirmar)) {
          return;
        }
        var dados = new FormData(form);
        var alvo = form.getAttribute('data-url') || url;
        fetch(alvo, {
          method: 'POST',
          body: dados,
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
          .then(function (r) { return r.text(); })
          .then(function (html) {
            var conteudo = extrairConteudo(html);
            if (conteudo === null) {
              corpo.insertAdjacentHTML(
                'afterbegin',
                '<p style="padding:10px;color:#b91c1c">' +
                'Não foi possível concluir a operação.</p>');
              return;
            }
            corpo.innerHTML = conteudo;
            // O POST passou (a tela voltou renderizada): marca para
            // atualizar a listagem no fechamento.
            houveAlteracao = true;
            ligarFormularios(corpo, url);
          })
          .catch(function () {
            corpo.insertAdjacentHTML(
              'afterbegin',
              '<p style="padding:10px;color:#b91c1c">' +
              'Não foi possível concluir a operação.</p>');
          });
      });
    });
  }

  document.addEventListener('click', function (event) {
    var botao = event.target.closest('.js-baixas-modal');
    if (!botao) return;
    event.preventDefault();
    abrir(botao.dataset.url);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && overlay && overlay.style.display === 'flex') {
      fechar();
    }
  });
})();

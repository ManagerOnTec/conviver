/**
 * ============================================================================
 * ADMIN CHANGELIST — BARRA DE AÇÕES ÚNICA E ROLAGEM DA TABELA
 * ============================================================================
 * O template (templates/admin/change_list.html) monta UMA barra de ações
 * acima da tabela (AGENTS.md, item 10):
 *
 *   [◀ ▶]  [ação em lote ▾ Executar]        [Adicionar] [Salvar]
 *   ─────────────────────────────────────────────────────────────
 *   tabela (cabeçalho fixo, rola nos dois eixos)
 *
 * Este script cuida do que é comportamento:
 *   1. SETAS ◀ ▶ — rolam a tabela para os lados (a barra do rodapé fica longe
 *      demais para uso corrente);
 *   2. ARRASTAR a tabela com o mouse (clique + arrastar) rola na horizontal;
 *   3. reposiciona a barra de ações, caso o Django a coloque BAIXO da tabela;
 *   4. a faixa de rolagem acima da tabela fica em sincronia com a tabela;
 *   5. ALTURA do quadro: usa todo o espaço livre até o pé da janela, então a
 *      listagem mostra a página inteira (~99 linhas) e rola por dentro.
 */
(function () {
  'use strict';

  // ------------------------------------------------------------------------
  // 1. Setas de rolagem horizontal
  // ------------------------------------------------------------------------
  function iniciarSetasDeRolagem() {
    var btnEsq = document.getElementById('admin-scroll-left');
    var btnDir = document.getElementById('admin-scroll-right');
    if (!btnEsq || !btnDir) return;

    /**
     * O SCROLLER real da tabela: o `.results` agora rola nos dois eixos, mas
     * se algum tema/css o deixar com `overflow: visible` quem rola é o
     * elemento pai. Escolher o que realmente tem conteúdo excedente evita
     * “a seta não faz nada”.
     */
    function scroller() {
      var res = document.querySelector('#changelist .results');
      if (res && res.scrollWidth > res.clientWidth + 2) return res;
      var atual = res && res.parentElement;
      while (atual && atual !== document.body) {
        if (atual.scrollWidth > atual.clientWidth + 2) return atual;
        atual = atual.parentElement;
      }
      return res;
    }

    function passo(el) {
      return Math.max(320, Math.round((el ? el.clientWidth : 900) * 0.75));
    }

    /**
     * Move para a posição `alvo`. `scroll-behavior: smooth` (css) fazia o
     * `scrollLeft +=` somar sobre um valor AINDA em animação e a rolagem
     * “voltava” (~11px). Aqui o destino é CALCULADO sobre a posição atual
     * real e aplicado sem animação (`behavior: 'instant'`) — previsível.
     */
    function rolar(direcao) {
      var el = scroller();
      if (!el) return;
      var maximo = Math.max(0, el.scrollWidth - el.clientWidth);
      var alvo = el.scrollLeft + direcao * passo(el);
      alvo = Math.max(0, Math.min(maximo, alvo));
      if (typeof el.scrollTo === 'function') {
        try {
          el.scrollTo({ left: alvo, top: el.scrollTop, behavior: 'instant' });
        } catch (e) {
          el.scrollLeft = alvo;
        }
      } else {
        el.scrollLeft = alvo;
      }
      atualizarEstado();
    }

    function atualizarEstado() {
      var el = scroller();
      var maximo = el ? el.scrollWidth - el.clientWidth : 0;
      btnEsq.disabled = !el || el.scrollLeft <= 2;
      btnDir.disabled = !el || el.scrollLeft >= maximo - 2;
      var nav = btnEsq.parentNode;
      if (nav) nav.style.display = maximo > 2 ? '' : 'none';
    }

    btnEsq.addEventListener('click', function (e) {
      e.preventDefault();
      rolar(-1);
    });
    btnDir.addEventListener('click', function (e) {
      e.preventDefault();
      rolar(1);
    });
    (scroller() || document).addEventListener('scroll', atualizarEstado, true);
    window.addEventListener('resize', atualizarEstado);
    atualizarEstado();
    setTimeout(atualizarEstado, 400);

    // Atalhos: Alt+←/→ rolam a tabela.
    document.addEventListener('keydown', function (e) {
      if (!e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      var tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      e.preventDefault();
      if (e.key === 'ArrowLeft') btnEsq.click();
      else btnDir.click();
    });
  }

  // ------------------------------------------------------------------------
  // 2. Arrastar a tabela com o mouse (rolagem horizontal)
  // ------------------------------------------------------------------------
  function iniciarArrastarTabela() {
    var results = document.querySelector('#changelist .results');
    if (!results || results.dataset.arrastavel === '1') return;
    results.dataset.arrastavel = '1';
    results.classList.add('js-arrastavel');

    var ativo = false;
    var xInicial = 0;
    var scrollInicial = 0;

    results.addEventListener('mousedown', function (e) {
      // Não arrasta quando o clique é em controle (checkbox, input, link).
      if (e.target.closest('input, select, textarea, a, button, label')) return;
      ativo = true;
      xInicial = e.pageX;
      scrollInicial = results.scrollLeft;
      results.classList.add('js-arrastando');
    });

    document.addEventListener('mousemove', function (e) {
      if (!ativo) return;
      e.preventDefault();
      results.scrollLeft = scrollInicial - (e.pageX - xInicial);
    });

    document.addEventListener('mouseup', function () {
      ativo = false;
      results.classList.remove('js-arrastando');
    });
  }

  // ------------------------------------------------------------------------
  // 3. Barra de ações ACIMA da tabela (se o Django a tiver posto embaixo)
  // ------------------------------------------------------------------------
  function posicionarBarraDeAcoes() {
    var form = document.getElementById('changelist-form');
    if (!form) return;
    var tabela = form.querySelector('#result_list') || form.querySelector('table');
    var barra = document.getElementById('admin-action-bar');
    if (!tabela || !barra) return;

    var destino = tabela.closest('.results') || tabela;
    if (barra.compareDocumentPosition(destino) & Node.DOCUMENT_POSITION_FOLLOWING) {
      return; // já está acima
    }
    destino.parentNode.insertBefore(barra, destino);
  }

  // ------------------------------------------------------------------------
  // 4. Faixa de rolagem no TOPO da tabela (espelha a rolagem da tabela)
  // ------------------------------------------------------------------------
  function criarFaixaRolagem(results) {
    if (!results || results.previousElementSibling &&
        results.previousElementSibling.classList.contains('js-scroll-topo')) return;
    var faixa = document.createElement('div');
    faixa.className = 'js-scroll-topo';
    faixa.setAttribute('aria-hidden', 'true');
    var espelho = document.createElement('div');
    espelho.className = 'js-scroll-topo-espelho';
    faixa.appendChild(espelho);
    results.parentNode.insertBefore(faixa, results);

    var sincronizando = false;
    faixa.addEventListener('scroll', function () {
      if (sincronizando) return;
      sincronizando = true;
      results.scrollLeft = faixa.scrollLeft;
      sincronizando = false;
    });
    results.addEventListener('scroll', function () {
      if (sincronizando) return;
      sincronizando = true;
      faixa.scrollLeft = results.scrollLeft;
      sincronizando = false;
    });

    var ajustar = function () {
      espelho.style.width = results.scrollWidth + 'px';
      faixa.style.display = results.scrollWidth > results.clientWidth ? 'block' : 'none';
    };
    ajustar();
    window.addEventListener('resize', ajustar);
    setTimeout(ajustar, 200);
  }

  function iniciarFaixaRolagem() {
    document.querySelectorAll('#changelist .results').forEach(criarFaixaRolagem);
  }

  // ------------------------------------------------------------------------
  // 5. Altura do QUADRO da tabela e `top` do cabeçalho
  // ------------------------------------------------------------------------
  /**
   * O quadro (`.results`) é o scroller e ocupa todo o espaço abaixo da barra
   * de ações:
   *
   *   altura = janela − (tudo que vem ACIMA do quadro) − folga
   *
   * É o que mantém os três pedidos ao mesmo tempo: a página não rola (barra e
   * cabeçalho estáveis, um nunca atrás do outro), as SETAS e a barra de
   * rolagem lateral têm conteúdo excedente para percorrer e a PAGINAÇÃO é
   * alcançada rolando dentro do quadro.
   */
  /**
   * CABEÇALHO FIXO abaixo da barra de ações.
   *
   * A página rola normalmente (breadcrumb, filtros e a tabela sobem), mas a
   * barra de ações e o `<thead>` ficam presos na janela. O `<thead>` recebe
   * `position: fixed` e é posicionado a cada scroll:
   *
   *   • `top`  = altura da barra de ações (fica logo abaixo dela);
   *   • `left`/`width` = posição e largura da tabela (colunas alinhadas);
   *   • `translateX` = `-scrollLeft` (acompanha a rolagem lateral).
   *
   * Ele só fica fixo enquanto a tabela estiver visível: antes dela aparece o
   * cabeçalho original no lugar, e depois do fim da tabela ele sai para a
   * PAGINAÇÃO poder ser vista.
   */
  function ajustarCabecalhoFixo() {
    var results = document.querySelector('#changelist .results');
    var tabela = document.getElementById('result_list');
    if (!results || !tabela) return;
    var thead = tabela.querySelector('thead');
    if (!thead) return;

    // Altura da barra de ações (é ela que fica presa no topo da janela).
    var barra = document.getElementById('admin-action-bar');
    var alturaBarra = 0;
    if (barra) {
      var estBarra = getComputedStyle(barra);
      if (estBarra.display !== 'none' && estBarra.visibility !== 'hidden') {
        alturaBarra = Math.round(barra.getBoundingClientRect().height);
      }
    }
    document.documentElement.style.setProperty(
      '--admin-thead-top', alturaBarra + 'px');

    var rq = results.getBoundingClientRect();
    // Faixa visível da tabela: do topo do quadro até o fim do quadro.
    var inicio = rq.top;
    var fim = rq.bottom;
    var limite = alturaBarra + (thead.offsetHeight || 0);

    // Só fica fixo quando o cabeçalho já passou por baixo da barra E ainda
    // há linhas na tela (antes do fim do quadro).
    var fixar = inicio < alturaBarra + 1 && fim > limite + 8;

    if (fixar) {
      thead.classList.add('thead-fixo');
      thead.style.left = Math.round(rq.left) + 'px';
      thead.style.width = Math.round(rq.width) + 'px';
      // ROLA JUNTO: o deslocamento é EXATAMENTE o mesmo do `scrollLeft` do
      // quadro, sem arredondamento — daí a sincronia perfeita com a tabela.
      thead.style.transform = 'translateX(' + (-results.scrollLeft) + 'px)';
      copiarLargurasDasColunas(tabela, thead);
    } else {
      thead.classList.remove('thead-fixo');
      thead.style.left = '';
      thead.style.width = '';
      thead.style.transform = '';
      limparLargurasDasColunas(thead);
    }
  }

  /**
   * Copia a largura REAL de cada coluna do corpo para o `<th>` correspondente.
   *
   * Sem isto o `<thead>` (`position: fixed`, com `table-layout: fixed`) usava
   * larguras próprias e, ao rolar lateralmente, as colunas do cabeçalho
   * saíam de cima do conteúdo.
   */
  function copiarLargurasDasColunas(tabela, thead) {
    var corpo = tabela.querySelector('tbody tr');
    if (!corpo) return;
    var ths = [...thead.querySelectorAll('th')];
    var tds = [...corpo.children];

    // O `<tbody>` começa com a célula do CHECKBOX; o `<thead>` montado pelo
    // template já traz o cabeçalho dessa coluna como PRIMEIRO `th`
    // (`action-checkbox-column`). Quando as contagens não batem, alinha-se
    // pelo FIM (a última coluna é sempre a mesma nos dois) — assim nenhuma
    // coluna fica deslocada.
    var deslocamento = tds.length - ths.length;
    for (var i = 0; i < ths.length; i++) {
      var td = tds[i + deslocamento];
      if (!td) continue;
      var largura = td.getBoundingClientRect().width;
      if (largura > 0) {
        ths[i].style.width = largura + 'px';
        ths[i].style.minWidth = largura + 'px';
        ths[i].style.maxWidth = largura + 'px';
      }
    }
  }

  function limparLargurasDasColunas(thead) {
    thead.querySelectorAll('th').forEach(function (th) {
      th.style.width = '';
      th.style.minWidth = '';
      th.style.maxWidth = '';
    });
  }

  function ajustarBarraFixa() {
    ajustarCabecalhoFixo();
  }

  function agendarBarraFixa() {
    // Roda várias vezes: fontes, imagens e o CSS do tema chegam depois do
    // DOM e mudam a altura da barra.
    ajustarBarraFixa();
    requestAnimationFrame(ajustarBarraFixa);
    [120, 300, 600, 1200].forEach(function (ms) {
      setTimeout(ajustarBarraFixa, ms);
    });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(ajustarBarraFixa).catch(function () {});
    }
  }

  window.addEventListener('load', agendarBarraFixa);

  function iniciar() {
    posicionarBarraDeAcoes();
    iniciarSetasDeRolagem();
    iniciarArrastarTabela();
    iniciarFaixaRolagem();
    agendarBarraFixa();
    window.addEventListener('resize', agendarBarraFixa);
    // A barra de ações pode mudar de altura (quebra de linha, fonte maior):
    // ao rolar, recalcula o `top` do cabeçalho para ele nunca entrar nela.
    window.addEventListener('scroll', function () {
      ajustarBarraFixa();
    }, { passive: true });
    // Rolagem LATERAL do quadro: o cabeçalho fixo acompanha (translateX).
    var quadro = document.querySelector('#changelist .results');
    if (quadro) {
      quadro.addEventListener('scroll', ajustarCabecalhoFixo, { passive: true });
    }
    if (window.ResizeObserver) {
      try {
        new ResizeObserver(ajustarBarraFixa).observe(
          document.getElementById('admin-action-bar') || document.body);
      } catch (e) { /* sem ResizeObserver: fica com o cálculo no load */ }
    }
    // Abrir/fechar painéis muda o que fica acima da tabela: recalcula.
    document.querySelectorAll('[data-panel-toggle], #btn-toggle-dashboard,' +
      '#btn-toggle-top-filter, #btn-toggle-breadcrumbs, #btn-toggle-left-sidebar')
      .forEach(function (btn) {
        btn.addEventListener('click', function () { setTimeout(ajustarBarraFixa, 60); });
      });
    setTimeout(function () {
      posicionarBarraDeAcoes();
      iniciarFaixaRolagem();
      ajustarBarraFixa();
    }, 150);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

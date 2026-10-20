/**
 * ============================================================================
 * CONVIVER - PRESCRIÇÃO PADRÃO (MODAL DE INSERÇÃO)
 * ============================================================================
 * Abre o modal de modelos de prescrição (PrescricaoPadrao) liberados para o
 * profissional (via ParametrosPrescricao) e ACRESCENTA os itens do modelo ao
 * formset da prescrição em cadastro, sem interferir na lógica existente de
 * adicionar/remover itens (prescricao_cadastrar.html).
 *
 * Requer no template:
 *   - <script id="prescricao-padrao-config" type="application/json">...</script>
 *     com {url, formsetPrefix, atendimentoId}
 *   - o modal parcial templates/parciais/_prescricao_padrao_modal.html
 *
 * Remoção: bash .rollback/2026-10-20_prescricao_padrao/rollback.sh
 */
(function () {
  'use strict';

  var state = {
    carregado: false,
    carregando: false,
    modelos: [],
    config: null
  };

  function getConfig() {
    if (state.config) return state.config;
    var el = document.getElementById('prescricao-padrao-config');
    if (!el) return null;
    try {
      state.config = JSON.parse(el.textContent || '{}');
    } catch (e) {
      console.error('[prescricao-padrao] JSON de configuração inválido', e);
      state.config = {};
    }
    return state.config;
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normalize(texto) {
    return String(texto == null ? '' : texto)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  function abrirModal() {
    var modalEl = document.getElementById('modalPrescricaoPadrao');
    if (!modalEl) return;
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
    if (!state.carregado && !state.carregando) {
      carregarModelos();
    }
  }

  function carregarModelos() {
    var cfg = getConfig();
    if (!cfg || !cfg.url) {
      exibirVazio();
      return;
    }
    state.carregando = true;
    mostrarLoading();

    fetch(cfg.url, {
      method: 'GET',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        state.modelos = Array.isArray(data) ? data : [];
        state.carregado = true;
        renderizar(state.modelos);
      })
      .catch(function (err) {
        console.error('[prescricao-padrao] falha ao carregar modelos', err);
        state.modelos = [];
        exibirVazio('Não foi possível carregar as prescrições padrão.');
      })
      .finally(function () {
        state.carregando = false;
      });
  }

  function mostrarLoading() {
    var loading = document.getElementById('loadingPrescricaoPadrao');
    var lista = document.getElementById('listaPrescricaoPadraoContainer');
    var vazio = document.getElementById('vazioPrescricaoPadrao');
    if (loading) loading.style.display = '';
    if (lista) lista.style.display = 'none';
    if (vazio) vazio.style.display = 'none';
  }

  function exibirVazio(mensagem) {
    var loading = document.getElementById('loadingPrescricaoPadrao');
    var lista = document.getElementById('listaPrescricaoPadraoContainer');
    var vazio = document.getElementById('vazioPrescricaoPadrao');
    if (loading) loading.style.display = 'none';
    if (lista) { lista.style.display = 'none'; lista.innerHTML = ''; }
    if (vazio) {
      if (mensagem) {
        var p = vazio.querySelector('p.text-muted');
        if (p) p.textContent = mensagem;
      }
      vazio.style.display = '';
    }
  }

  function renderizar(modelos) {
    var loading = document.getElementById('loadingPrescricaoPadrao');
    var container = document.getElementById('listaPrescricaoPadraoContainer');
    var vazio = document.getElementById('vazioPrescricaoPadrao');
    if (loading) loading.style.display = 'none';

    if (!modelos || !modelos.length) {
      exibirVazio();
      return;
    }
    if (vazio) vazio.style.display = 'none';

    container.innerHTML = '';
    modelos.forEach(function (modelo) {
      container.appendChild(criarCard(modelo));
    });
    container.style.display = '';

    // Reaplica o filtro atual, se houver texto digitado
    var filtro = document.getElementById('filtroPrescricaoPadraoInput');
    if (filtro && filtro.value) aplicarFiltro(filtro.value);
  }

  function criarCard(modelo) {
    var card = document.createElement('div');
    card.className = 'card border-0 shadow-sm prescricao-padrao-card';
    card.dataset.modeloId = modelo.id;

    var itensHtml = (modelo.itens || []).map(function (item) {
      var badges = '';
      if (item.se_necessario) badges += ' <span class="badge bg-warning text-dark">SN</span>';
      if (item.dose_unica) badges += ' <span class="badge bg-info text-dark">Dose única</span>';
      var obs = item.observacao ? ' <small class="text-muted">(' + esc(item.observacao) + ')</small>' : '';
      return '<li class="small py-1 border-bottom">' +
        '<i class="fas fa-capsules text-primary me-1"></i>' +
        '<b>' + esc(item.produto) + '</b>' +
        ' <span class="text-muted">/ ' + esc(item.unidade) + ' / ' + esc(item.via) + '</span>' +
        '<br><span class="text-muted ms-3">' +
        '<i class="far fa-clock me-1"></i>' + esc(item.intervalo_horas) +
        ' &nbsp;|&nbsp; <i class="fas fa-hourglass-start me-1"></i>' + esc(item.hora_inicio_produto) +
        '</span>' + badges + obs +
        '</li>';
    }).join('');

    card.innerHTML =
      '<div class="card-body p-3">' +
        '<div class="d-flex justify-content-between align-items-start gap-2">' +
          '<div>' +
            '<h6 class="fw-bold mb-1"><i class="fas fa-file-prescription text-primary me-1"></i>' + esc(modelo.descricao) + '</h6>' +
            '<div class="small text-muted">' +
              '<i class="fas fa-user-shield me-1"></i>' + esc(modelo.liberacao) +
              ' &nbsp;|&nbsp; <i class="fas fa-list me-1"></i>' + esc(modelo.total_itens) + ' item(ns)' +
            '</div>' +
            (modelo.observacao ? '<div class="small fst-italic text-secondary mt-1">' + esc(modelo.observacao) + '</div>' : '') +
          '</div>' +
          '<button type="button" class="btn btn-sm btn-primary btn-inserir-prescricao-padrao text-nowrap" data-modelo-id="' + esc(modelo.id) + '">' +
            '<i class="fas fa-plus me-1"></i>Inserir' +
          '</button>' +
        '</div>' +
        '<ul class="list-unstyled mt-2 mb-0">' + itensHtml + '</ul>' +
      '</div>';
    return card;
  }

  function aplicarFiltro(termo) {
    var q = normalize(termo);
    var cards = document.querySelectorAll('#listaPrescricaoPadraoContainer .prescricao-padrao-card');
    var visiveis = 0;
    cards.forEach(function (card) {
      var texto = normalize(card.textContent);
      var mostrar = !q || texto.indexOf(q) !== -1;
      card.style.display = mostrar ? '' : 'none';
      if (mostrar) visiveis++;
    });
    var btnLimpar = document.getElementById('btnLimparFiltroPrescricaoPadrao');
    if (btnLimpar) btnLimpar.style.display = termo ? '' : 'none';

    var container = document.getElementById('listaPrescricaoPadraoContainer');
    if (container) container.style.display = visiveis ? '' : 'none';
    var vazio = document.getElementById('vazioPrescricaoPadrao');
    if (vazio && state.modelos.length) {
      vazio.style.display = visiveis ? 'none' : '';
      var p = vazio.querySelector('p.text-muted');
      if (p && !visiveis) p.textContent = 'Nenhuma prescrição padrão corresponde à pesquisa.';
    }
  }

  function inserirModelo(modeloId) {
    var modelo = state.modelos.find(function (m) { return String(m.id) === String(modeloId); });
    if (!modelo || !modelo.itens || !modelo.itens.length) {
      alert('Esta prescrição padrão não possui itens ativos.');
      return;
    }
    var inseridos = 0;
    modelo.itens.forEach(function (item) {
      if (adicionarItemNoFormset(item)) inseridos++;
    });

    if (!inseridos) {
      alert('Não foi possível inserir os itens. Verifique se o formulário está aberto corretamente.');
      return;
    }

    var modalEl = document.getElementById('modalPrescricaoPadrao');
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    mostrarToast(inseridos + ' item(ns) de “' + modelo.descricao + '” inserido(s).');
  }

  /**
   * Adiciona um item no formset existente usando o mesmo padrão do botão
   * "#btn-adicionar-item" (TOTAL_FORMS + clonagem do template __prefix__),
   * porém SEM duplicar a lógica de remoção/reindexação.
   */
  function adicionarItemNoFormset(item) {
    var cfg = getConfig() || {};
    var prefix = cfg.formsetPrefix;
    if (!prefix) return false;

    var emptyTpl = document.getElementById(prefix + '-empty');
    var container = document.getElementById('itens-prescricao');
    var totalForms = document.getElementById('id_' + prefix + '-TOTAL_FORMS');
    if (!emptyTpl || !container || !totalForms) return false;

    var index = parseInt(totalForms.value, 10) || 0;
    var html = emptyTpl.innerHTML.replace(/__prefix__/g, index);
    var wrapper = document.createElement('div');
    wrapper.innerHTML = html.trim();
    var novoItem = wrapper.firstElementChild;
    if (!novoItem) return false;

    // Mesma manipulação feita pelo script original em #btn-adicionar-item
    novoItem.querySelectorAll('input, select, textarea').forEach(function (el) {
      if (el.type === 'hidden') return;
      el.classList.add('form-control');
      if (el.id) el.id = el.id.replace(new RegExp(prefix + '-\\d+-'), prefix + '-' + index + '-');
      if (el.name) el.name = el.name.replace(new RegExp(prefix + '-\\d+-'), prefix + '-' + index + '-');
    });
    novoItem.querySelectorAll('label').forEach(function (el) {
      el.classList.add('control-label');
      if (el.htmlFor) el.htmlFor = el.htmlFor.replace(new RegExp(prefix + '-\\d+-'), prefix + '-' + index + '-');
    });

    container.appendChild(novoItem);
    totalForms.value = index + 1;

    var row = novoItem.querySelector('.row') || novoItem;
    preencherItem(row, prefix, index, item);

    if (window.jQuery && jQuery.fn.select2) {
      jQuery(row).find('select').select2({ width: '100%' });
    }
    return true;
  }

  function setValor(row, seletor, valor) {
    if (valor === undefined || valor === null) return;
    var el = row.querySelector(seletor);
    if (!el) return;
    el.value = String(valor);
    // Mantém o Select2 (quando aplicado) sincronizado com o value
    if (window.jQuery && jQuery(el).data('select2')) {
      jQuery(el).trigger('change.select2');
    }
  }

  function setCheck(row, seletor, marcado) {
    var el = row.querySelector(seletor);
    if (!el) return;
    el.checked = !!marcado;
  }

  function preencherItem(row, prefix, index, item) {
    var base = 'id_' + prefix + '-' + index + '-';
    setValor(row, 'select[name="' + prefix + '-' + index + '-produto"]', item.produto_id);
    setValor(row, 'select[name="' + prefix + '-' + index + '-intervalo_horas"]', item.intervalo_horas_id);
    setValor(row, 'select[name="' + prefix + '-' + index + '-hora_inicio_produto"]', item.hora_inicio_produto_id);
    setCheck(row, '#' + base + 'se_necessario', item.se_necessario);
    setCheck(row, '#' + base + 'dose_unica', item.dose_unica);
    setValor(row, 'input[name="' + prefix + '-' + index + '-observacao"]', item.observacao || '');
    // Auditoria: identifica no POST qual item do modelo de prescrição foi usado.
    // A view (PrescricaoCreateView) remove este campo da cópia usada pelo formset
    // principal e usa o valor apenas para registrar PrescricaoPadraoUtilizacao.
    var origem = row.querySelector('input.item_padrao_id');
    if (!origem) {
      origem = document.createElement('input');
      origem.type = 'hidden';
      origem.className = 'item_padrao_id';
      origem.name = prefix + '-' + index + '-item_padrao_id';
      row.appendChild(origem);
    }
    origem.value = item.id;
  }

  function mostrarToast(mensagem) {
    var anterior = document.querySelector('.prescricao-padrao-toast');
    if (anterior) anterior.remove();

    var toast = document.createElement('div');
    toast.className = 'prescricao-padrao-toast';
    toast.style.cssText =
      'position:fixed;top:18px;right:18px;z-index:2000;background:#fff;border-left:4px solid #198754;' +
      'box-shadow:0 6px 18px rgba(0,0,0,.18);border-radius:8px;padding:10px 16px;font-size:.9rem;';
    toast.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i>' + esc(mensagem);
    document.body.appendChild(toast);
    setTimeout(function () {
      toast.style.transition = 'opacity .3s ease';
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3200);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('btn-inserir-prescricao-padrao');
    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        abrirModal();
      });
    }

    var filtro = document.getElementById('filtroPrescricaoPadraoInput');
    if (filtro) {
      filtro.addEventListener('input', function () { aplicarFiltro(filtro.value); });
    }

    var btnLimpar = document.getElementById('btnLimparFiltroPrescricaoPadrao');
    if (btnLimpar) {
      btnLimpar.addEventListener('click', function () {
        if (filtro) { filtro.value = ''; aplicarFiltro(''); filtro.focus(); }
      });
    }

    document.addEventListener('click', function (e) {
      var alvo = e.target.closest('.btn-inserir-prescricao-padrao');
      if (!alvo) return;
      e.preventDefault();
      inserirModelo(alvo.dataset.modeloId);
    });

    // Pré-carrega a lista quando o usuário passa o mouse/foca o botão (percepção de rapidez)
    if (btn) {
      btn.addEventListener('mouseenter', function () {
        if (!state.carregado && !state.carregando) carregarModelos();
      }, { once: true });
    }
  });
})();

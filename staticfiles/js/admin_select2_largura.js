/**
 * ============================================================================
 * ADMIN — SELECT2 DE DIGITAÇÃO (autocomplete) COM LARGURA CORRETA
 * ============================================================================
 * O widget `autocomplete_fields` do Django grava `style="width: NNNpx"` inline
 * no `.select2-container` no momento da inicialização. Como essa medição ocorre
 * antes do CSS custom do tema ser aplicado (o formulário ainda sem layout), o
 * campo ficava com ~73px — visualmente vazio e sem espaço para digitar.
 *
 * Este script, carregado apenas no admin de prescrição (ver
 * admin_prescricoes/admin_prescricao_padrao.py), recalcula a largura do select2
 * para 100% do espaço disponível, preservando os botões +, lápis e x do Django.
 *
 * Remoção: bash .rollback/2026-10-20_prescricao_padrao/rollback.sh
 */
(function () {
  'use strict';

  function ajustarLarguraSelect2() {
    if (!window.django || !window.django.jQuery) return;
    var $ = window.django.jQuery;

    $('.select2-container').each(function () {
      var $container = $(this);
      if ($container.data('larguraAjustada')) return;

      var $wrapper = $container.closest('.related-widget-wrapper');
      var largura = 0;

      if ($wrapper.length) {
        // Os botões +, lápis e x são posicionados em fluxo ao lado do select.
        // Medimos o espaço de cada um pela própria caixa deles.
        var ocupado = 0;
        $wrapper.children('a, span.related-widget-wrapper-link, .related-widget-wrapper-link')
          .each(function () {
            var $el = $(this);
            if (!$el.is(':visible')) return;
            ocupado += ($el.outerWidth() || 0) + (parseFloat($el.css('margin-right')) || 0);
          });
        var larguraWrapper = $wrapper.width() || 0;
        largura = larguraWrapper > ocupado + 120
          ? larguraWrapper - ocupado - 2
          : Math.max(larguraWrapper, 220);
      } else {
        largura = $container.parent().width() || 0;
      }

      if (!largura) return;

      $container.css({ width: largura + 'px', 'max-width': '100%' });
      $container.find('.select2-selection--single').css({ width: '100%' });
      $container.data('larguraAjustada', true);
    });
  }

  function iniciar() {
    ajustarLarguraSelect2();
    // O Django inicializa os autocompletes em `domready`; reforçamos após o layout.
    setTimeout(ajustarLarguraSelect2, 60);
    setTimeout(ajustarLarguraSelect2, 350);
    setTimeout(ajustarLarguraSelect2, 900);

    // Inlines: cada linha nova ("Adicionar outro") precisa do mesmo ajuste.
    if (window.django && window.django.jQuery) {
      window.django.jQuery(document).on(
        'formset:added',
        function () { setTimeout(ajustarLarguraSelect2, 60); }
      );
    }

    // Recalcula ao redimensionar / abrir painéis do tema.
    window.addEventListener('resize', ajustarLarguraSelect2);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

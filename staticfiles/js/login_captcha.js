(function () {
    'use strict';

    var imageBox = document.getElementById('captcha-image');
    var tokenInput = document.getElementById('id_captcha_token');
    var answerInput = document.getElementById('id_captcha');
    var reloadBtn = document.getElementById('captcha-reload');

    if (!imageBox || !tokenInput || !answerInput) {
        return;
    }

    // URLs resolvidas pelo template (data-attributes no wrapper).
    var wrapper = document.getElementById('captcha-wrapper');
    var desafioUrl = (wrapper && wrapper.dataset.desafioUrl) || '/captcha/desafio/';

    function mostrarErro(msg) {
        imageBox.innerHTML = '<span class="auth-captcha-loading is-error">' +
            '<i class="fas fa-triangle-exclamation"></i> ' + msg + '</span>';
    }

    function renderSvg(svg, token) {
        imageBox.innerHTML = svg;
        tokenInput.value = token;
    }

    function carregarNovo() {
        imageBox.innerHTML = '<span class="auth-captcha-loading">' +
            '<i class="fas fa-spinner fa-spin"></i> Carregando...</span>';

        fetch(desafioUrl, {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { 'Accept': 'application/json' }
        })
            .then(function (resp) {
                return resp.json().then(function (data) {
                    return { ok: resp.ok, data: data };
                });
            })
            .then(function (res) {
                if (!res.ok || !res.data.ok) {
                    mostrarErro((res.data && res.data.erro) || 'Falha ao carregar.');
                    return;
                }
                renderSvg(res.data.svg, res.data.token);
                answerInput.value = '';
                answerInput.focus();
            })
            .catch(function () {
                mostrarErro('Falha ao carregar a verificação.');
            });
    }

    if (reloadBtn) {
        reloadBtn.addEventListener('click', function (e) {
            e.preventDefault();
            carregarNovo();
        });
    }

    // Normaliza entrada: remove espaços e força maiúsculas.
    answerInput.addEventListener('input', function () {
        var pos = this.selectionStart;
        this.value = this.value.replace(/\s+/g, '').toUpperCase();
        try { this.setSelectionRange(pos, pos); } catch (err) { /* noop */ }
    });

    var captchaBox = wrapper || imageBox;
    if (captchaBox.hasAttribute('data-auto-load')) {
        carregarNovo();
    }
})();

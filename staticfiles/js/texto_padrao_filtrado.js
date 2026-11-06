/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - TEXTOS PADRONIZADOS PARA DOCUMENTOS
 * Atas | Oficios | Orcamentos  ->  admin_relatorios.TextoDocumentoPadrao
 * ============================================================================
 * Fonte de dados : /texto-padrao/<tipo>/   (atas | oficios | orcamentos)
 * Controle total do modal (sem Bootstrap), carregamento por tipo e inserção
 * no editor TinyMCE (com fallback para textarea).
 */
(function () {
    'use strict';

    var MODAL_SEL = '#modalDocumentoTextoPadrao';
    var BACKDROP_ID = 'backdropDocumentoTextoPadrao';
    var LABELS = { atas: 'Ata', oficios: 'Ofício', orcamentos: 'Orçamento' };
    var TIPOS = { ata: 'atas', atas: 'atas', oficio: 'oficios', oficios: 'oficios', orcamento: 'orcamentos', orcamentos: 'orcamentos' };

    function normalizarTipo(valor) {
        var v = String(valor || '').toLowerCase().trim();
        return TIPOS[v] || 'atas';
    }

    /* ---------------- EDITOR ---------------- */
    function getEditor() {
        if (typeof tinymce === 'undefined') return null;
        var ids = ['id_ata', 'ata', 'id_oficio', 'oficio', 'id_orcamento', 'orcamento'];
        for (var i = 0; i < ids.length; i++) {
            var ed = tinymce.get(ids[i]);
            if (ed) return ed;
        }
        if (tinymce.activeEditor && !tinymce.activeEditor.isHidden()) return tinymce.activeEditor;
        return null;
    }

    function getTextarea() {
        return document.getElementById('id_ata') ||
               document.getElementById('id_oficio') ||
               document.getElementById('id_orcamento') ||
               document.querySelector('form textarea');
    }

    function inserirTexto(html) {
        var parsed = String(html || '').trim();
        if (!parsed) return false;

        var editor = getEditor();
        if (editor) {
            editor.focus();
            editor.execCommand('mceInsertContent', false, parsed);
            editor.save();
            return true;
        }

        var ta = getTextarea();
        if (ta) {
            var tmp = document.createElement('div');
            tmp.innerHTML = parsed;
            var texto = (tmp.textContent || '').trim();
            var pos = (typeof ta.selectionStart === 'number') ? ta.selectionStart : ta.value.length;
            var antes = ta.value.slice(0, pos);
            var depois = ta.value.slice(pos);
            ta.value = antes + (antes && !/\n$/.test(antes) ? '\n' : '') + texto + depois;
            ta.focus();
            return true;
        }
        return false;
    }

    /* ---------------- TOAST ---------------- */
    function toast(msg) {
        var old = document.querySelector('.clinical-toast-notification');
        if (old) old.parentNode.removeChild(old);

        var el = document.createElement('div');
        el.className = 'clinical-toast-notification';
        var icon = document.createElement('i');
        icon.className = 'fas fa-check-circle text-success';
        var span = document.createElement('span');
        span.textContent = msg;
        el.appendChild(icon);
        el.appendChild(span);
        document.body.appendChild(el);

        setTimeout(function () {
            el.style.transition = 'opacity .3s ease, transform .3s ease';
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            setTimeout(function () {
                if (el.parentNode) el.parentNode.removeChild(el);
            }, 300);
        }, 3000);
    }

    /* ---------------- MODAL ---------------- */
    function abrirModal(modal) {
        if (!modal) return;
        if (modal.parentNode !== document.body) document.body.appendChild(modal);

        if (!document.getElementById(BACKDROP_ID)) {
            var bd = document.createElement('div');
            bd.id = BACKDROP_ID;
            bd.className = 'modal-backdrop fade show';
            bd.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:#000;opacity:.45;z-index:2147482000;';
            document.body.appendChild(bd);
        }

        modal.style.display = 'block';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.zIndex = '2147483000';
        modal.style.overflowX = 'hidden';
        modal.style.overflowY = 'auto';
        modal.classList.add('show');
        modal.setAttribute('aria-modal', 'true');
        modal.removeAttribute('aria-hidden');

        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
    }

    function fecharModal(modal) {
        if (!modal) return;
        modal.style.display = 'none';
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        modal.removeAttribute('aria-modal');

        var bd = document.getElementById(BACKDROP_ID);
        if (bd && bd.parentNode) bd.parentNode.removeChild(bd);

        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    }

    /* ---------------- RENDER ---------------- */
    function construirCard(item, tipo, onInsert) {
        var card = document.createElement('div');
        card.className = 'clinical-text-card';

        var header = document.createElement('div');
        header.className = 'clinical-card-header';

        var title = document.createElement('h6');
        title.className = 'clinical-card-title';
        var ico = document.createElement('i');
        ico.className = 'fas fa-file-lines text-primary';
        title.appendChild(ico);
        title.appendChild(document.createTextNode(' ' + (item.descricao || 'Sem descrição')));

        var badges = document.createElement('div');
        badges.className = 'clinical-card-badges';
        var badge = document.createElement('span');
        badge.className = 'badge bg-primary-subtle text-primary border border-primary-subtle small px-2 py-1';
        badge.textContent = LABELS[tipo] || 'Documento';
        badges.appendChild(badge);

        header.appendChild(title);
        header.appendChild(badges);

        var tmp = document.createElement('div');
        tmp.innerHTML = item.texto || '';
        var preview = document.createElement('div');
        preview.className = 'clinical-card-preview';
        var txt = (tmp.textContent || '').replace(/\s+/g, ' ').trim();
        if (txt.length > 300) txt = txt.substring(0, 300) + '...';
        preview.textContent = txt || 'Sem conteúdo disponível';

        var actions = document.createElement('div');
        actions.className = 'clinical-card-actions';

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn-insert-clinical-text';
        var plus = document.createElement('i');
        plus.className = 'fas fa-plus';
        btn.appendChild(plus);
        btn.appendChild(document.createTextNode(' Inserir no Documento'));
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            onInsert(item);
        });

        actions.appendChild(btn);
        card.appendChild(header);
        card.appendChild(preview);
        card.appendChild(actions);
        return card;
    }

    /* ---------------- ASSISTENTE ---------------- */
    function criarAssistente() {
        var button = document.getElementById('insertDefaultDocs');
        var modal = document.querySelector(MODAL_SEL);
        if (!button || !modal) return null;

        var loading = document.getElementById('loadingDocTexto');
        var container = document.getElementById('listaDocTextosContainer');
        var vazio = document.getElementById('vazioDocTexto');
        var filtro = document.getElementById('filtroDocTextoInput');
        var limpar = document.getElementById('btnLimparFiltroDocTexto');

        var estado = { tipo: 'atas', dados: [], carregando: false, carregadoPara: null };

        if (modal.parentNode !== document.body) document.body.appendChild(modal);

        function onInsert(item) {
            if (inserirTexto(item.texto)) {
                fecharModal(modal);
                toast('Texto "' + (item.descricao || '') + '" inserido com sucesso!');
            } else {
                toast('Não foi possível localizar o editor do documento.');
            }
        }

        function renderizar(lista) {
            if (!container || !vazio) return;
            container.innerHTML = '';

            if (!lista || !lista.length) {
                container.style.display = 'none';
                vazio.style.display = 'block';
                return;
            }

            vazio.style.display = 'none';
            container.style.display = 'flex';

            for (var i = 0; i < lista.length; i++) {
                container.appendChild(construirCard(lista[i], estado.tipo, onInsert));
            }
        }

        function carregar(tipo) {
            if (estado.carregando) return;
            estado.carregando = true;

            if (loading) loading.style.display = 'block';
            if (container) {
                container.style.display = 'none';
                container.innerHTML = '';
            }
            if (vazio) vazio.style.display = 'none';

            var url = '/texto-padrao/' + encodeURIComponent(tipo) + '/?_=' + new Date().getTime();

            fetch(url, {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return res.json();
                })
                .then(function (dados) {
                    estado.dados = Array.isArray(dados) ? dados : [];
                    estado.carregadoPara = tipo;
                    if (loading) loading.style.display = 'none';
                    renderizar(estado.dados);
                })
                .catch(function (err) {
                    console.error('[Texto Padrão] ' + err.message);
                    if (loading) loading.style.display = 'none';
                    if (container) container.style.display = 'none';
                    if (vazio) {
                        vazio.style.display = 'block';
                        var p = vazio.querySelector('p');
                        if (p) p.textContent = 'Não foi possível carregar os textos padronizados (' + err.message + ').';
                    }
                })
                .then(function () { estado.carregando = false; });
        }

        function abrir(tipo) {
            estado.tipo = normalizarTipo(tipo || button.getAttribute('data-tipo-documento'));
            if (filtro) filtro.value = '';
            if (limpar) limpar.style.display = 'none';
            abrirModal(modal);
            carregar(estado.tipo);
        }

        button.addEventListener('click', function (e) {
            e.preventDefault();
            button.setAttribute('data-aberto-pelo-direto', '1');
            abrir(button.getAttribute('data-tipo-documento'));
        }, true);

        modal.querySelectorAll('[data-bs-dismiss], [data-dismiss]').forEach(function (el) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                fecharModal(modal);
            });
        });

        document.addEventListener('click', function (e) {
            if (e.target && e.target.id === BACKDROP_ID) fecharModal(modal);
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal.classList.contains('show')) fecharModal(modal);
        });

        if (filtro) {
            filtro.addEventListener('input', function () {
                var q = this.value.trim().toLowerCase();
                if (limpar) limpar.style.display = q ? 'inline-block' : 'none';
                renderizar(estado.dados.filter(function (it) {
                    return (it.descricao || '').toLowerCase().indexOf(q) !== -1 ||
                           (it.texto || '').toLowerCase().indexOf(q) !== -1;
                }));
            });
        }

        if (limpar) {
            limpar.addEventListener('click', function () {
                if (filtro) { filtro.value = ''; filtro.focus(); }
                limpar.style.display = 'none';
                renderizar(estado.dados);
            });
        }

        return { abrir: abrir, carregar: carregar, estado: estado };
    }

    /* ---------------- BOOT ROBUSTO ---------------- */
    var assistente = null;

    function boot() {
        if (assistente) return;
        assistente = criarAssistente();
        if (!assistente) {
            console.warn('[Texto Padrao] Botao #insertDefaultDocs ou modal ausente. Nova tentativa em 300ms...');
            setTimeout(boot, 300);
        } else {
            console.info('[Texto Padrao] Assistente inicializado.');
        }
    }

    /* Tentativas de inicializacao em pontos diferentes do ciclo de vida */
    boot();
    document.addEventListener('DOMContentLoaded', boot);
    window.addEventListener('load', boot);
    setTimeout(boot, 500);
    setTimeout(boot, 1500);

    /* Fallback: delegacao de evento no document (caso o listener direto nao exista) */
    document.addEventListener('click', function (e) {
        var alvo = (e.target && e.target.closest) ? e.target.closest('#insertDefaultDocs') : null;
        if (!alvo) return;
        if (!assistente) boot();
        if (!assistente) return;
        if (alvo.getAttribute('data-aberto-pelo-direto') === '1') {
            alvo.removeAttribute('data-aberto-pelo-direto');
            return;
        }
        e.preventDefault();
        assistente.abrir(alvo.getAttribute('data-tipo-documento'));
    });

    /* API global para abertura manual (debug / integracoes) */
    window.AssistenteDocumentos = {
        abrir: function (tipo) {
            if (!assistente) boot();
            if (assistente) assistente.abrir(tipo);
        },
        estado: function () { return assistente ? assistente.estado : null; }
    };
})();

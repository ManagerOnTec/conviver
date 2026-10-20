/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - ASSISTENTE DE TEXTOS PADRONIZADOS PARA DOCUMENTOS
 * (Atas, Ofícios e Orçamentos)
 * ============================================================================
 * - Abre o modal acima de qualquer elemento (backdrop sem cobrir o conteudo);
 * - Carrega os textos de admin_relatorios.TextoDocumentoPadrao via AJAX,
 *   filtrados estritamente pelo tipo (atas / oficios / orcamentos);
 * - Insere o texto no editor TinyMCE (ou textarea) na posicao do cursor.
 */
(function () {
    'use strict';

    function getDocumentEditor() {
        if (typeof tinymce === 'undefined') return null;
        var ids = ['id_ata', 'ata', 'id_oficio', 'oficio', 'id_orcamento', 'orcamento'];
        for (var i = 0; i < ids.length; i++) {
            var ed = tinymce.get(ids[i]);
            if (ed) return ed;
        }
        if (tinymce.activeEditor && !tinymce.activeEditor.isHidden()) return tinymce.activeEditor;
        return null;
    }

    function getDocumentTextarea() {
        return document.getElementById('id_ata') ||
               document.getElementById('id_oficio') ||
               document.getElementById('id_orcamento') ||
               document.querySelector('form textarea');
    }

    function parseDocumentHtml(html) {
        var parser = new DOMParser();
        return parser.parseFromString(html || '', 'text/html').body.innerHTML;
    }

    function insertHtmlIntoDocument(html) {
        var parsed = parseDocumentHtml(html).trim();
        if (!parsed) return;

        var editor = getDocumentEditor();
        if (editor) {
            editor.focus();
            var current = (editor.getContent({ format: 'html' }) || '').trim();
            var empty = ['', '<p></p>', '<p><br data-mce-bogus="1"></p>', '<p>&nbsp;</p>'];
            if (empty.indexOf(current) !== -1) {
                editor.setContent(parsed);
            } else {
                editor.execCommand('mceInsertContent', false, parsed);
            }
            editor.save();
            return;
        }

        var ta = getDocumentTextarea();
        if (ta) {
            var clean = parsed.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').trim();
            var pos = typeof ta.selectionStart === 'number' ? ta.selectionStart : ta.value.length;
            var before = ta.value.slice(0, pos);
            var after = ta.value.slice(pos);
            ta.value = before + (before && !/\n$/.test(before) ? '\n' : '') + clean + after;
            ta.focus();
        }
    }

    function showToast(message) {
        var existing = document.querySelector('.clinical-toast-notification');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.className = 'clinical-toast-notification';
        var icon = document.createElement('i');
        icon.className = 'fas fa-check-circle text-success';
        var span = document.createElement('span');
        span.textContent = message;
        toast.appendChild(icon);
        toast.appendChild(span);
        document.body.appendChild(toast);

        setTimeout(function () {
            toast.style.transition = 'opacity .3s ease, transform .3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            setTimeout(function () { toast.remove(); }, 300);
        }, 3000);
    }

    function abrirModal(modalEl) {
        if (!modalEl) return;

        if (modalEl.parentElement !== document.body) {
            document.body.appendChild(modalEl);
        }

        var backdrop = document.getElementById('backdropDocumentoTextoPadrao');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'backdropDocumentoTextoPadrao';
            backdrop.className = 'modal-backdrop fade show';
            backdrop.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:#000;opacity:.45;z-index:999990;';
            document.body.appendChild(backdrop);
        }

        modalEl.classList.add('show');
        modalEl.style.cssText = 'display:block;position:fixed;inset:0;width:100vw;height:100vh;z-index:999999;overflow-y:auto;';
        modalEl.removeAttribute('aria-hidden');
        modalEl.setAttribute('aria-modal', 'true');

        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';

        var dialog = modalEl.querySelector('.modal-dialog');
        if (dialog) {
            dialog.style.zIndex = '1000000';
            dialog.style.position = 'relative';
            dialog.style.pointerEvents = 'auto';
        }
    }

    function fecharModal(modalEl) {
        if (!modalEl) return;

        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.removeAttribute('aria-modal');

        var backdrop = document.getElementById('backdropDocumentoTextoPadrao');
        if (backdrop) backdrop.remove();

        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    }

    function init() {
        var button = document.getElementById('insertDefaultDocs');
        var modalEl = document.getElementById('modalDocumentoTextoPadrao');
        if (!button || !modalEl) return;
        if (button.dataset.assistentePronto === '1') return;
        button.dataset.assistentePronto = '1';

        var filtroInput = document.getElementById('filtroDocTextoInput');
        var btnLimparFiltro = document.getElementById('btnLimparFiltroDocTexto');
        var loadingEl = document.getElementById('loadingDocTexto');
        var containerEl = document.getElementById('listaDocTextosContainer');
        var vazioEl = document.getElementById('vazioDocTexto');

        var textosCarregados = [];
        var tipoAtual = '';

        if (modalEl.parentElement !== document.body) {
            document.body.appendChild(modalEl);
        }

        modalEl.querySelectorAll('[data-bs-dismiss], [data-dismiss]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                fecharModal(modalEl);
            });
        });

        document.addEventListener('click', function (e) {
            if (e.target && e.target.id === 'backdropDocumentoTextoPadrao') {
                fecharModal(modalEl);
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modalEl.classList.contains('show')) {
                fecharModal(modalEl);
            }
        });

        function normalizarTipo(valor) {
            var mapa = {
                'ata': 'atas', 'atas': 'atas',
                'oficio': 'oficios', 'oficios': 'oficios',
                'orcamento': 'orcamentos', 'orcamentos': 'orcamentos'
            };
            var chave = (valor || '').toLowerCase().trim();
            return mapa[chave] || 'atas';
        }

        function abrir() {
            tipoAtual = normalizarTipo(button.getAttribute('data-tipo-documento'));
            abrirModal(modalEl);
            carregarTextos(tipoAtual);
        }

        button.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            abrir();
        }, true);

        /* Fallback: se Bootstrap abrir o modal por data-bs-toggle */
        modalEl.addEventListener('show.bs.modal', function () {
            tipoAtual = normalizarTipo(button.getAttribute('data-tipo-documento'));
            carregarTextos(tipoAtual);
        });

        function carregarTextos(tipo) {
            if (loadingEl) loadingEl.style.display = 'block';
            if (containerEl) {
                containerEl.style.display = 'none';
                containerEl.innerHTML = '';
            }
            if (vazioEl) vazioEl.style.display = 'none';

            var url = '/texto-padrao/' + encodeURIComponent(tipo) + '/?t=' + Date.now();

            fetch(url, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return res.json();
                })
                .then(function (data) {
                    textosCarregados = Array.isArray(data) ? data : [];
                    renderizar(textosCarregados, tipo);
                })
                .catch(function (err) {
                    console.error('[Texto Padrao] ' + err.message);
                    if (loadingEl) loadingEl.style.display = 'none';
                    if (vazioEl) {
                        vazioEl.style.display = 'block';
                        var p = vazioEl.querySelector('p');
                        if (p) p.textContent = 'Nao foi possivel consultar o catalogo de textos padronizados.';
                    }
                });
        }

        function renderizar(lista, tipo) {
            if (loadingEl) loadingEl.style.display = 'none';

            if (!lista || lista.length === 0) {
                if (containerEl) containerEl.style.display = 'none';
                if (vazioEl) vazioEl.style.display = 'block';
                return;
            }

            if (vazioEl) vazioEl.style.display = 'none';
            if (!containerEl) return;

            var labels = { 'atas': 'Ata', 'oficios': 'Oficio', 'orcamentos': 'Orcamento' };

            containerEl.innerHTML = '';
            containerEl.style.display = 'flex';

            lista.forEach(function (item) {
                var card = document.createElement('div');
                card.className = 'clinical-text-card';

                var header = document.createElement('div');
                header.className = 'clinical-card-header';

                var title = document.createElement('h6');
                title.className = 'clinical-card-title';
                var iconEl = document.createElement('i');
                iconEl.className = 'fas fa-file-lines text-primary';
                title.appendChild(iconEl);
                title.appendChild(document.createTextNode(' ' + (item.descricao || 'Sem descricao')));

                var badges = document.createElement('div');
                badges.className = 'clinical-card-badges';
                var badge = document.createElement('span');
                badge.className = 'badge bg-primary-subtle text-primary border border-primary-subtle small px-2 py-1';
                badge.textContent = labels[tipo] || 'Documento';
                badges.appendChild(badge);

                header.appendChild(title);
                header.appendChild(badges);

                var prev = document.createElement('div');
                prev.innerHTML = item.texto || '';

                var preview = document.createElement('div');
                preview.className = 'clinical-card-preview';
                preview.textContent = (prev.textContent || '').trim().substring(0, 320) || 'Sem conteudo disponivel';

                var actions = document.createElement('div');
                actions.className = 'clinical-card-actions';

                var insertBtn = document.createElement('button');
                insertBtn.type = 'button';
                insertBtn.className = 'btn-insert-clinical-text';
                var plus = document.createElement('i');
                plus.className = 'fas fa-plus';
                insertBtn.appendChild(plus);
                insertBtn.appendChild(document.createTextNode(' Inserir no Documento'));

                insertBtn.addEventListener('click', function () {
                    insertHtmlIntoDocument(item.texto);
                    fecharModal(modalEl);
                    showToast('Texto "' + (item.descricao || '') + '" inserido com sucesso!');
                });

                actions.appendChild(insertBtn);
                card.appendChild(header);
                card.appendChild(preview);
                card.appendChild(actions);
                containerEl.appendChild(card);
            });
        }

        if (filtroInput) {
            filtroInput.addEventListener('input', function () {
                var query = (this.value || '').trim().toLowerCase();
                if (btnLimparFiltro) btnLimparFiltro.style.display = query ? 'inline-block' : 'none';

                var filtrados = textosCarregados.filter(function (item) {
                    var desc = (item.descricao || '').toLowerCase();
                    var texto = (item.texto || '').toLowerCase();
                    return desc.indexOf(query) !== -1 || texto.indexOf(query) !== -1;
                });

                renderizar(filtrados, tipoAtual);
            });
        }

        if (btnLimparFiltro) {
            btnLimparFiltro.addEventListener('click', function () {
                if (!filtroInput) return;
                filtroInput.value = '';
                filtroInput.focus();
                btnLimparFiltro.style.display = 'none';
                renderizar(textosCarregados, tipoAtual);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

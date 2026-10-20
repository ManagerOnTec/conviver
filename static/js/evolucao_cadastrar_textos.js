/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - ASSISTENTE CLÍNICO DE TEXTOS E DIAGNÓSTICOS (JS)
 * ============================================================================
 * Abre leque de opções por Tipo de Evolução e Textos Padronizados cadastrados,
 * além de inserção de diagnósticos (CID) com feedback e usabilidade aprimorada.
 */

function decodeHtmlEntities(value) {
    const parser = new DOMParser();
    return parser.parseFromString(value ?? '', 'text/html').documentElement.textContent || '';
}

function normalizeEditorHtml(html) {
    return (html || '').replace(/<p><\/p>/g, '');
}

function getEvolutionEditor() {
    return (typeof tinymce !== 'undefined') ? (tinymce.get('id_evolucao') || tinymce.get('evolucao')) : null;
}

function insertHtmlIntoEvolution(html, options) {
    options = options || {};
    const prepend = options.prepend || false;
    const editor = getEvolutionEditor();

    if (!editor) {
        // Fallback para textarea normal se TinyMCE não estiver ativo
        const textarea = document.getElementById('id_evolucao') || document.getElementById('evolucao');
        if (textarea) {
            const cleanText = decodeHtmlEntities(html).replace(/<[^>]+>/g, '');
            if (prepend) {
                textarea.value = cleanText + '\n\n' + textarea.value;
            } else {
                textarea.value += (textarea.value ? '\n' : '') + cleanText;
            }
        }
        return;
    }

    const sanitizedHtml = normalizeEditorHtml(decodeHtmlEntities(html));
    if (!sanitizedHtml) {
        return;
    }

    if (prepend) {
        const currentContent = editor.getContent();
        const separator = currentContent ? '<br>' : '';
        editor.setContent(`${sanitizedHtml}${separator}${currentContent}`);
        return;
    }

    editor.focus();
    editor.execCommand('mceInsertContent', false, sanitizedHtml);
}

/**
 * Toast de Feedback Visual
 */
function showClinicalToast(mensagem, icone) {
    icone = icone || 'fas fa-check-circle';
    const existing = document.querySelector('.clinical-toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'clinical-toast-notification';
    toast.innerHTML = '<i class="' + icone + ' text-success"></i> <span>' + mensagem + '</span>';
    document.body.appendChild(toast);

    setTimeout(function () {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(function () { toast.remove(); }, 300);
    }, 3200);
}

document.addEventListener('DOMContentLoaded', function () {
    // ------------------------------------------------------------------------
    // 1. GERENCIAMENTO DO MODAL DE TEXTOS PADRONIZADOS COM LEQUE POR TIPO
    // ------------------------------------------------------------------------
    const btnTextoPadrao = document.getElementById('insertDefaultText');
    const modalTextosEl = document.getElementById('modalTextosPadrao');
    const filtroInput = document.getElementById('filtroTextoPadraoInput');
    const btnLimparFiltro = document.getElementById('btnLimparFiltroTextos');
    const loadingTextos = document.getElementById('loadingTextosPadrao');
    const containerTextos = document.getElementById('listaTextosPadraoContainer');
    const vazioTextos = document.getElementById('vazioTextosPadrao');

    let textosCarregados = [];
    let modalTextosInstance = null;

    // Move os modais diretamente para o body para que fiquem acima do backdrop e de qualquer stacking context
    if (modalTextosEl && modalTextosEl.parentElement !== document.body) {
        document.body.appendChild(modalTextosEl);
    }

    if (btnTextoPadrao && modalTextosEl) {
        btnTextoPadrao.addEventListener('click', function (e) {
            e.preventDefault();
            if (modalTextosEl.parentElement !== document.body) {
                document.body.appendChild(modalTextosEl);
            }
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                modalTextosInstance = bootstrap.Modal.getOrCreateInstance(modalTextosEl);
                modalTextosInstance.show();
            }

            // Carrega os textos se ainda não foram carregados
            if (textosCarregados.length === 0) {
                carregarTextosPadrao();
            }
        });
    }

    function carregarTextosPadrao() {
        if (loadingTextos) loadingTextos.style.display = 'block';
        if (containerTextos) containerTextos.style.display = 'none';
        if (vazioTextos) vazioTextos.style.display = 'none';

        fetch('/prontuarios/textopadrao_filtrado/')
            .then(function (res) {
                if (!res.ok) throw new Error('Erro ao carregar textos');
                return res.json();
            })
            .then(function (data) {
                textosCarregados = data || [];
                renderizarTextos(textosCarregados);
            })
            .catch(function (err) {
                console.error(err);
                if (loadingTextos) loadingTextos.style.display = 'none';
                if (vazioTextos) {
                    vazioTextos.style.display = 'block';
                    vazioTextos.querySelector('p').textContent = 'Erro ao consultar o catálogo de textos padronizados.';
                }
            });
    }

    /**
     * Renderiza o leque estruturado: Nível 1 = Tipos de Evolução, Nível 2 = Textos Cadastrados
     */
    function renderizarTextos(lista) {
        if (loadingTextos) loadingTextos.style.display = 'none';

        if (!lista || lista.length === 0) {
            if (containerTextos) containerTextos.style.display = 'none';
            if (vazioTextos) vazioTextos.style.display = 'block';
            return;
        }

        if (vazioTextos) vazioTextos.style.display = 'none';
        if (containerTextos) {
            containerTextos.innerHTML = '';
            containerTextos.style.display = 'flex';

            // Agrupa por Tipo de Evolução
            const grupos = {};
            lista.forEach(function (item) {
                const tipoNome = (item.tipo_evolucao__tipo_evolucao || '').trim() || 'Geral / Outros';
                if (!grupos[tipoNome]) {
                    grupos[tipoNome] = [];
                }
                grupos[tipoNome].push(item);
            });

            // Detecta tipo selecionado no formulário atual
            const selectTipo = document.getElementById('id_tipo_evolucao');
            const tipoAtual = selectTipo && selectTipo.selectedIndex >= 0 ? selectTipo.options[selectTipo.selectedIndex].text.trim().toLowerCase() : '';

            let primeiroGrupo = true;

            // Cria o leque (accordion) por Tipo de Evolução
            Object.keys(grupos).sort().forEach(function (nomeTipo) {
                const itensDoTipo = grupos[nomeTipo];
                const matchAtual = tipoAtual && nomeTipo.toLowerCase().includes(tipoAtual);
                const deveIniciarAberto = matchAtual || primeiroGrupo;
                primeiroGrupo = false;

                const accordionItem = document.createElement('div');
                accordionItem.className = 'tipo-evolucao-accordion-item' + (deveIniciarAberto ? '' : ' collapsed');

                // Cabeçalho do Tipo de Evolução (Leque Nível 1)
                const header = document.createElement('div');
                header.className = 'tipo-evolucao-header';
                header.title = 'Clique para expandir/recolher os modelos de ' + nomeTipo;
                header.innerHTML =
                    '<h6><i class="fas fa-folder-open"></i> ' + nomeTipo + '</h6>' +
                    '<div class="d-flex align-items-center gap-2">' +
                        '<span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill">' + itensDoTipo.length + ' modelo(s)</span>' +
                        '<i class="fas fa-chevron-down chevron-icon"></i>' +
                    '</div>';

                // Corpo com os Textos Padrão Cadastrados (Leque Nível 2)
                const body = document.createElement('div');
                body.className = 'tipo-evolucao-body';

                itensDoTipo.forEach(function (item) {
                    const card = document.createElement('div');
                    card.className = 'clinical-text-card';

                    const profBadge = item.profissao__profissao ? '<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle small px-2 py-1"><i class="fas fa-user-md me-1"></i>' + item.profissao__profissao + '</span>' : '';

                    const divTemp = document.createElement('div');
                    divTemp.innerHTML = item.texto || '';
                    const previewText = divTemp.textContent.trim() || 'Sem conteúdo disponível';

                    card.innerHTML =
                        '<div class="clinical-card-header">' +
                            '<h6 class="clinical-card-title"><i class="fas fa-file-lines text-primary"></i> ' + item.descricao + '</h6>' +
                            '<div class="clinical-card-badges">' + profBadge + '</div>' +
                        '</div>' +
                        '<div class="clinical-card-preview">' + previewText + '</div>' +
                        '<div class="clinical-card-actions">' +
                            '<button type="button" class="btn-insert-clinical-text" title="Inserir este texto no editor">' +
                                '<i class="fas fa-plus"></i> Inserir Texto' +
                            '</button>' +
                        '</div>';

                    card.querySelector('.btn-insert-clinical-text').addEventListener('click', function (e) {
                        e.stopPropagation();
                        insertHtmlIntoEvolution(item.texto);
                        if (modalTextosInstance) modalTextosInstance.hide();
                        showClinicalToast('Texto "' + item.descricao + '" inserido com sucesso!');
                    });

                    body.appendChild(card);
                });

                // Alternância do leque ao clicar no cabeçalho do tipo
                header.addEventListener('click', function () {
                    accordionItem.classList.toggle('collapsed');
                });

                accordionItem.appendChild(header);
                accordionItem.appendChild(body);
                containerTextos.appendChild(accordionItem);
            });
        }
    }

    // Filtro instantâneo no modal de textos (filtra por descrição, tipo ou texto)
    if (filtroInput) {
        filtroInput.addEventListener('input', function () {
            const query = (this.value || '').trim().toLowerCase();
            if (btnLimparFiltro) {
                btnLimparFiltro.style.display = query ? 'inline-block' : 'none';
            }

            const filtrados = textosCarregados.filter(function (item) {
                const desc = (item.descricao || '').toLowerCase();
                const tipo = (item.tipo_evolucao__tipo_evolucao || '').toLowerCase();
                const prof = (item.profissao__profissao || '').toLowerCase();
                const textoPuro = (item.texto || '').toLowerCase();
                return desc.includes(query) || tipo.includes(query) || prof.includes(query) || textoPuro.includes(query);
            });

            renderizarTextos(filtrados);

            // Quando houver busca ativa, abre todos os leques para facilitar a visualização imediata
            if (query && containerTextos) {
                containerTextos.querySelectorAll('.tipo-evolucao-accordion-item').forEach(function (el) {
                    el.classList.remove('collapsed');
                });
            }
        });
    }

    if (btnLimparFiltro) {
        btnLimparFiltro.addEventListener('click', function () {
            if (filtroInput) {
                filtroInput.value = '';
                filtroInput.focus();
                renderizarTextos(textosCarregados);
                btnLimparFiltro.style.display = 'none';
            }
        });
    }

    // ------------------------------------------------------------------------
    // 2. GERENCIAMENTO DO MODAL DE DIAGNÓSTICOS (CID)
    // ------------------------------------------------------------------------
    const btnBuscarDiag = document.getElementById('btn-buscar-diagnosticos');
    const modalDiagEl = document.getElementById('modalDiagnosticos');
    const loadingDiag = document.getElementById('loadingDiagnosticos');
    const conteudoDiag = document.getElementById('conteudoDiagnosticos');
    const listaDiagCheckbox = document.getElementById('listaDiagnosticosCheckbox');
    const vazioDiag = document.getElementById('vazioDiagnosticos');
    const btnToggleTodos = document.getElementById('btnToggleTodosDiagnosticos');
    const btnConfirmarDiag = document.getElementById('btnConfirmarInserirDiagnosticos');

    let modalDiagInstance = null;
    let diagnosticosAtuais = [];

    // Move modal de diagnósticos para o body
    if (modalDiagEl && modalDiagEl.parentElement !== document.body) {
        document.body.appendChild(modalDiagEl);
    }

    if (btnBuscarDiag && modalDiagEl) {
        btnBuscarDiag.addEventListener('click', function (e) {
            e.preventDefault();
            if (modalDiagEl.parentElement !== document.body) {
                document.body.appendChild(modalDiagEl);
            }
            const atendimentoId = this.getAttribute('data-atendimento-id');
            if (!atendimentoId) {
                alert('ID do atendimento não localizado.');
                return;
            }

            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                modalDiagInstance = bootstrap.Modal.getOrCreateInstance(modalDiagEl);
                modalDiagInstance.show();
            }

            carregarDiagnosticos(atendimentoId);
        });
    }

    function carregarDiagnosticos(atendimentoId) {
        if (loadingDiag) loadingDiag.style.display = 'block';
        if (conteudoDiag) conteudoDiag.style.display = 'none';
        if (vazioDiag) vazioDiag.style.display = 'none';
        if (btnConfirmarDiag) btnConfirmarDiag.style.display = 'none';

        fetch('/prontuarios/buscar_diagnosticos/' + atendimentoId + '/')
            .then(function (res) { return res.json(); })
            .then(function (data) {
                diagnosticosAtuais = data.diagnosticos || [];
                renderizarDiagnosticos(diagnosticosAtuais);
            })
            .catch(function (err) {
                console.error(err);
                if (loadingDiag) loadingDiag.style.display = 'none';
                if (vazioDiag) {
                    vazioDiag.style.display = 'block';
                    vazioDiag.querySelector('p').textContent = 'Erro ao consultar os diagnósticos do atendimento.';
                }
            });
    }

    function renderizarDiagnosticos(lista) {
        if (loadingDiag) loadingDiag.style.display = 'none';

        if (!lista || lista.length === 0) {
            if (conteudoDiag) conteudoDiag.style.display = 'none';
            if (vazioDiag) vazioDiag.style.display = 'block';
            if (btnConfirmarDiag) btnConfirmarDiag.style.display = 'none';
            return;
        }

        if (vazioDiag) vazioDiag.style.display = 'none';
        if (conteudoDiag) conteudoDiag.style.display = 'block';
        if (btnConfirmarDiag) btnConfirmarDiag.style.display = 'inline-block';

        if (listaDiagCheckbox) {
            listaDiagCheckbox.innerHTML = '';
            lista.forEach(function (cid) {
                const item = document.createElement('label');
                item.className = 'diagnostic-check-item';
                item.innerHTML = 
                    '<input type="checkbox" class="cid-select-check" value="' + cid + '" checked>' +
                    '<span class="diagnostic-check-label"><i class="fas fa-tag text-info me-2"></i>' + cid + '</span>';
                listaDiagCheckbox.appendChild(item);
            });
        }
    }

    if (btnToggleTodos) {
        btnToggleTodos.addEventListener('click', function () {
            const checks = document.querySelectorAll('.cid-select-check');
            const algumDesmarcado = Array.from(checks).some(function (c) { return !c.checked; });
            checks.forEach(function (c) { c.checked = algumDesmarcado; });
            btnToggleTodos.textContent = algumDesmarcado ? 'Desmarcar Todos' : 'Marcar Todos';
        });
    }

    if (btnConfirmarDiag) {
        btnConfirmarDiag.addEventListener('click', function () {
            const checks = Array.from(document.querySelectorAll('.cid-select-check:checked'));
            if (checks.length === 0) {
                alert('Selecione pelo menos um diagnóstico para inserir.');
                return;
            }

            const cidsTexto = checks.map(function (c) { return c.value; }).join(', ');
            const htmlParaInserir = '<strong>Diagnósticos (CID):</strong> ' + cidsTexto;

            const posInicio = document.getElementById('posInicio');
            const deveInserirNoInicio = posInicio && posInicio.checked;

            insertHtmlIntoEvolution(htmlParaInserir, { prepend: deveInserirNoInicio });

            if (modalDiagInstance) modalDiagInstance.hide();
            showClinicalToast(checks.length + ' diagnóstico(s) inserido(s) com sucesso!', 'fas fa-stethoscope');
        });
    }
});

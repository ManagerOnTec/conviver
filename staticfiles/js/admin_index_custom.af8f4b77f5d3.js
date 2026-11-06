/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - ADMIN INDEX INTERACTIVE DASHBOARD SCRIPT
 * ============================================================================
 * Gerencia a barra localizadora instantânea de módulos e funções,
 * abertura/fechamento das listas suspensas (accordions) e contadores em tempo real.
 */

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('adminModuleSearch');
    const clearBtn = document.getElementById('adminSearchClear');
    const resetBtn = document.getElementById('btnResetSearch');
    const modulesGrid = document.getElementById('adminModulesGrid');
    const noResultsBox = document.getElementById('noResultsBox');
    const statsModuleCount = document.getElementById('statsModuleCount');
    const statsModelCount = document.getElementById('statsModelCount');
    const btnExpandAll = document.getElementById('btnExpandAll');
    const btnCollapseAll = document.getElementById('btnCollapseAll');

    if (!modulesGrid) return;

    const moduleCols = Array.from(modulesGrid.querySelectorAll('.module-card-col'));

    /**
     * Atualiza contadores iniciais
     */
    function updateCounts() {
        let visibleModules = 0;
        let visibleModels = 0;

        moduleCols.forEach(col => {
            if (col.style.display !== 'none') {
                visibleModules++;
                const functions = col.querySelectorAll('.function-item');
                functions.forEach(fn => {
                    if (fn.style.display !== 'none') {
                        visibleModels++;
                    }
                });
            }
        });

        if (statsModuleCount) statsModuleCount.textContent = visibleModules;
        if (statsModelCount) statsModelCount.textContent = visibleModels;

        if (noResultsBox) {
            noResultsBox.style.display = (visibleModules === 0) ? 'block' : 'none';
        }
    }

    /**
     * Filtro localizador instantâneo
     */
    function filterModules() {
        const query = (searchInput.value || '').trim().toLowerCase();

        if (clearBtn) {
            clearBtn.style.display = query ? 'inline-block' : 'none';
        }

        moduleCols.forEach(col => {
            const card = col.querySelector('.module-card');
            const appName = (col.getAttribute('data-app-name') || '').toLowerCase();
            const appLabel = (col.getAttribute('data-app-label') || '').toLowerCase();
            const functions = Array.from(col.querySelectorAll('.function-item'));

            let appMatches = appName.includes(query) || appLabel.includes(query);
            let hasMatchingFunction = false;

            functions.forEach(fn => {
                const modelName = (fn.getAttribute('data-model-name') || '').toLowerCase();
                if (!query || modelName.includes(query) || appMatches) {
                    fn.style.display = '';
                    if (query && modelName.includes(query)) {
                        hasMatchingFunction = true;
                    }
                } else {
                    fn.style.display = 'none';
                }
            });

            if (!query) {
                // Estado normal
                col.style.display = '';
                functions.forEach(fn => fn.style.display = '');
            } else if (appMatches || hasMatchingFunction) {
                col.style.display = '';
                // Se a busca casou com alguma função interna, expande o card automaticamente
                if (card && (hasMatchingFunction || appMatches)) {
                    card.classList.add('expanded');
                }
            } else {
                col.style.display = 'none';
            }
        });

        updateCounts();
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterModules);
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                searchInput.value = '';
                filterModules();
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            searchInput.value = '';
            searchInput.focus();
            filterModules();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
            filterModules();
        });
    }

    /**
     * Alternância dos Accordions de Funções ao clicar no Cabeçalho
     */
    const cardHeaders = document.querySelectorAll('.module-card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', function (e) {
            // Evita propagação se clicar em links
            if (e.target.tagName.toLowerCase() === 'a') return;

            const card = header.closest('.module-card');
            if (card) {
                card.classList.toggle('expanded');
            }
        });
    });

    /**
     * Expandir / Recolher Todos
     */
    if (btnExpandAll) {
        btnExpandAll.addEventListener('click', function () {
            document.querySelectorAll('.module-card').forEach(card => card.classList.add('expanded'));
        });
    }

    if (btnCollapseAll) {
        btnCollapseAll.addEventListener('click', function () {
            document.querySelectorAll('.module-card').forEach(card => card.classList.remove('expanded'));
        });
    }

    /**
     * Alternância do Bloco Inferior de Atividades Recentes
     */
    const recentToggleHeader = document.getElementById('recentActionsBlockToggle');
    const recentGrid = document.getElementById('recentActionsGrid');
    const textRecentToggle = document.getElementById('textRecentToggle');
    const iconRecentToggle = document.getElementById('iconRecentToggle');

    if (recentToggleHeader && recentGrid) {
        const isCollapsed = localStorage.getItem('conviver_collapse_recent_block') === 'true';
        if (isCollapsed) {
            recentGrid.style.display = 'none';
            if (textRecentToggle) textRecentToggle.textContent = 'Expandir';
            if (iconRecentToggle) iconRecentToggle.className = 'fas fa-chevron-down';
        }

        recentToggleHeader.addEventListener('click', function () {
            const isHidden = recentGrid.style.display === 'none';
            recentGrid.style.display = isHidden ? 'grid' : 'none';
            localStorage.setItem('conviver_collapse_recent_block', !isHidden);
            if (textRecentToggle) textRecentToggle.textContent = isHidden ? 'Recolher' : 'Expandir';
            if (iconRecentToggle) iconRecentToggle.className = isHidden ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
        });
    }

    // Inicializa contagem
    updateCounts();
});

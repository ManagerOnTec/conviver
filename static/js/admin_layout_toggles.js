/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - DJANGO ADMIN LAYOUT TOGGLES
 * ============================================================================
 * Gerencia a visibilidade retrátil dos componentes do Django Admin:
 * 1. Menu lateral esquerdo de modelos (#nav-sidebar)
 * 2. Menu lateral direito de filtros (#changelist-filter)
 * 3. Menu superior de busca e filtros (#toolbar, #changelist-search)
 * 4. Breadcrumbs (migalhas de navegação)
 * 5. Modo Foco / Zen
 * 
 * Persiste preferências do usuário em localStorage e sincroniza com o Django.
 * Suporta atalhos de teclado (Alt+M, Alt+F, Alt+T, Alt+B, Alt+Z, Alt+R).
 */

(function () {
    'use strict';

    // Chaves de armazenamento
    const STORAGE_KEYS = {
        LEFT_SIDEBAR: 'conviver_hide_left_sidebar',
        RIGHT_FILTER: 'conviver_hide_right_filter',
        TOP_FILTER: 'conviver_hide_top_filter',
        BREADCRUMBS: 'conviver_hide_breadcrumbs',
        ZEN_MODE: 'conviver_zen_mode',
        ZEN_BACKUP: 'conviver_zen_backup_state'
    };

    // Estado local
    const state = {
        hideLeftSidebar: localStorage.getItem(STORAGE_KEYS.LEFT_SIDEBAR) === 'true',
        hideRightFilter: localStorage.getItem(STORAGE_KEYS.RIGHT_FILTER) === 'true',
        hideTopFilter: localStorage.getItem(STORAGE_KEYS.TOP_FILTER) === 'true',
        hideBreadcrumbs: localStorage.getItem(STORAGE_KEYS.BREADCRUMBS) === 'true',
        zenMode: localStorage.getItem(STORAGE_KEYS.ZEN_MODE) === 'true'
    };

    /**
     * Aplica classes no elemento <html> e <body>
     */
    function applyClasses() {
        const root = document.documentElement;
        const body = document.body;

        const toggleClass = (cls, condition) => {
            if (root) root.classList.toggle(cls, condition);
            if (body) body.classList.toggle(cls, condition);
        };

        toggleClass('hide-left-sidebar', state.hideLeftSidebar);
        toggleClass('hide-right-filter', state.hideRightFilter);
        toggleClass('hide-top-filter', state.hideTopFilter);
        toggleClass('hide-breadcrumbs', state.hideBreadcrumbs);

        // Sincroniza com navSidebar nativo do Django se presente
        const main = document.getElementById('main');
        const navSidebar = document.getElementById('nav-sidebar');
        if (main && navSidebar) {
            if (state.hideLeftSidebar) {
                main.classList.remove('shifted');
                navSidebar.setAttribute('aria-expanded', 'false');
                localStorage.setItem('django.admin.navSidebarIsOpen', 'false');
            } else {
                main.classList.add('shifted');
                navSidebar.setAttribute('aria-expanded', 'true');
                localStorage.setItem('django.admin.navSidebarIsOpen', 'true');
            }
        }
    }

    /**
     * Atualiza os botões da barra superior e do floating dock
     */
    function updateUIElements() {
        // 1. Menu Lateral
        updateButtonState('btn-toggle-left-sidebar', 'dock-item-left-sidebar', state.hideLeftSidebar, 'Menu Lateral');

        // 2. Breadcrumbs
        updateButtonState('btn-toggle-breadcrumbs', 'dock-item-breadcrumbs', state.hideBreadcrumbs, 'Breadcrumbs');

        // 3. Filtro Superior
        const hasTopFilter = !!(document.getElementById('toolbar') || document.getElementById('changelist-search'));
        updateButtonState('btn-toggle-top-filter', 'dock-item-top-filter', state.hideTopFilter, 'Filtro Topo', hasTopFilter);

        // 4. Filtros Direita
        const hasRightFilter = !!document.getElementById('changelist-filter');
        updateButtonState('btn-toggle-right-filter', 'dock-item-right-filter', state.hideRightFilter, 'Filtros', hasRightFilter);

        // Atualiza contagem de filtros ativos
        updateFilterBadge();

        // 5. Botão Modo Foco / Zen
        const btnFocus = document.getElementById('btn-toggle-focus-mode');
        const dockFocus = document.getElementById('dock-item-focus-mode');
        if (btnFocus) {
            btnFocus.classList.toggle('active-zen', state.zenMode);
            btnFocus.title = state.zenMode ? 'Sair do Modo Foco (Alt+Z)' : 'Ativar Modo Foco / Maximizar Tabela (Alt+Z)';
        }
        if (dockFocus) {
            const icon = dockFocus.querySelector('.dock-status-icon');
            if (icon) icon.textContent = state.zenMode ? '★' : '☆';
        }
    }

    /**
     * Atualiza o estado visual de um botão e item de dock específico
     */
    function updateButtonState(btnId, dockId, isHidden, labelText, isAvailable = true) {
        const btn = document.getElementById(btnId);
        if (btn) {
            if (!isAvailable) {
                btn.style.opacity = '0.45';
                btn.style.pointerEvents = 'none';
                btn.title = `${labelText} (Não aplicável nesta tela)`;
            } else {
                btn.style.opacity = '';
                btn.style.pointerEvents = '';
                btn.classList.toggle('is-hidden', isHidden);
                btn.title = isHidden ? `Exibir ${labelText}` : `Ocultar ${labelText}`;
            }
        }

        const dockItem = document.getElementById(dockId);
        if (dockItem) {
            const statusIcon = dockItem.querySelector('.dock-status-icon');
            if (statusIcon) {
                statusIcon.textContent = isHidden ? '✕' : '✓';
                statusIcon.style.color = isHidden ? '#dc3545' : '#28a745';
            }
            if (!isAvailable) {
                dockItem.style.opacity = '0.5';
                dockItem.style.pointerEvents = 'none';
            } else {
                dockItem.style.opacity = '';
                dockItem.style.pointerEvents = '';
            }
        }
    }

    /**
     * Conta quantos filtros estão atualmente ativos e exibe no badge
     */
    function updateFilterBadge() {
        const filterPane = document.getElementById('changelist-filter');
        let activeCount = 0;

        if (filterPane) {
            // No Django admin, filtros ativos possuem classe "selected" nos <li> ou links dentro de detalhes
            const selectedItems = filterPane.querySelectorAll('li.selected');
            selectedItems.forEach(item => {
                // Filtros padrão "Todos" não contam como filtro restritivo
                const linkText = (item.textContent || '').trim().toLowerCase();
                if (linkText !== 'todos' && linkText !== 'all' && linkText !== 'tudo') {
                    activeCount++;
                }
            });

            // Se ainda não encontrou via li.selected, verifica parâmetros de busca na URL
            if (activeCount === 0) {
                const params = new URLSearchParams(window.location.search);
                for (const [key, val] of params.entries()) {
                    if (key !== 'o' && key !== 'p' && key !== 'q' && key !== 'all' && val) {
                        activeCount++;
                    }
                }
            }
        }

        const badges = [
            document.getElementById('active-filters-count'),
            document.getElementById('dock-active-filters-count')
        ];

        badges.forEach(badge => {
            if (badge) {
                if (activeCount > 0) {
                    badge.textContent = activeCount;
                    badge.style.display = 'inline-block';
                    badge.classList.add('has-filters');
                    badge.title = `${activeCount} filtro(s) ativo(s) restringindo a listagem`;
                } else {
                    badge.style.display = 'none';
                    badge.classList.remove('has-filters');
                }
            }
        });
    }

    /**
     * Funções de Toggle Individuais
     */
    function toggleLeftSidebar(forceState) {
        state.hideLeftSidebar = (forceState !== undefined) ? forceState : !state.hideLeftSidebar;
        localStorage.setItem(STORAGE_KEYS.LEFT_SIDEBAR, state.hideLeftSidebar);
        applyClasses();
        updateUIElements();
    }

    function toggleRightFilter(forceState) {
        state.hideRightFilter = (forceState !== undefined) ? forceState : !state.hideRightFilter;
        localStorage.setItem(STORAGE_KEYS.RIGHT_FILTER, state.hideRightFilter);
        applyClasses();
        updateUIElements();
    }

    function toggleTopFilter(forceState) {
        state.hideTopFilter = (forceState !== undefined) ? forceState : !state.hideTopFilter;
        localStorage.setItem(STORAGE_KEYS.TOP_FILTER, state.hideTopFilter);
        applyClasses();
        updateUIElements();
    }

    function toggleBreadcrumbs(forceState) {
        state.hideBreadcrumbs = (forceState !== undefined) ? forceState : !state.hideBreadcrumbs;
        localStorage.setItem(STORAGE_KEYS.BREADCRUMBS, state.hideBreadcrumbs);
        applyClasses();
        updateUIElements();
    }

    /**
     * Modo Foco (Zen Mode):
     * Oculta tudo de uma vez para foco total na grade de dados.
     * Ao clicar de novo, restaura o estado anterior.
     */
    function toggleZenMode() {
        if (!state.zenMode) {
            // Salva estado atual antes de ativar o foco
            const backup = {
                hideLeftSidebar: state.hideLeftSidebar,
                hideRightFilter: state.hideRightFilter,
                hideTopFilter: state.hideTopFilter,
                hideBreadcrumbs: state.hideBreadcrumbs
            };
            localStorage.setItem(STORAGE_KEYS.ZEN_BACKUP, JSON.stringify(backup));

            // Oculta tudo
            state.hideLeftSidebar = true;
            state.hideRightFilter = true;
            state.hideTopFilter = true;
            state.hideBreadcrumbs = true;
            state.zenMode = true;
        } else {
            // Restaura do backup
            try {
                const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.ZEN_BACKUP) || '{}');
                state.hideLeftSidebar = !!saved.hideLeftSidebar;
                state.hideRightFilter = !!saved.hideRightFilter;
                state.hideTopFilter = !!saved.hideTopFilter;
                state.hideBreadcrumbs = !!saved.hideBreadcrumbs;
            } catch (e) {
                state.hideLeftSidebar = false;
                state.hideRightFilter = false;
                state.hideTopFilter = false;
                state.hideBreadcrumbs = false;
            }
            state.zenMode = false;
        }

        localStorage.setItem(STORAGE_KEYS.LEFT_SIDEBAR, state.hideLeftSidebar);
        localStorage.setItem(STORAGE_KEYS.RIGHT_FILTER, state.hideRightFilter);
        localStorage.setItem(STORAGE_KEYS.TOP_FILTER, state.hideTopFilter);
        localStorage.setItem(STORAGE_KEYS.BREADCRUMBS, state.hideBreadcrumbs);
        localStorage.setItem(STORAGE_KEYS.ZEN_MODE, state.zenMode);

        applyClasses();
        updateUIElements();
    }

    /**
     * Restaura visualização padrão (tudo visível)
     */
    function resetLayout() {
        state.hideLeftSidebar = false;
        state.hideRightFilter = false;
        state.hideTopFilter = false;
        state.hideBreadcrumbs = false;
        state.zenMode = false;

        localStorage.removeItem(STORAGE_KEYS.LEFT_SIDEBAR);
        localStorage.removeItem(STORAGE_KEYS.RIGHT_FILTER);
        localStorage.removeItem(STORAGE_KEYS.TOP_FILTER);
        localStorage.removeItem(STORAGE_KEYS.BREADCRUMBS);
        localStorage.removeItem(STORAGE_KEYS.ZEN_MODE);
        localStorage.removeItem(STORAGE_KEYS.ZEN_BACKUP);

        applyClasses();
        updateUIElements();
    }

    /**
     * Injeta botões de fechar diretamente nos painéis se ainda não existirem
     */
    function injectInlineCloseButtons() {
        // Botão de fechar dentro do título de #changelist-filter
        const filterPane = document.getElementById('changelist-filter');
        if (filterPane) {
            const h2 = filterPane.querySelector('h2');
            if (h2 && !h2.querySelector('.btn-close-filter-pane')) {
                const closeBtn = document.createElement('button');
                closeBtn.type = 'button';
                closeBtn.className = 'btn-close-filter-pane';
                closeBtn.title = 'Ocultar painel de filtros (Alt+F)';
                closeBtn.innerHTML = '✕';
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleRightFilter(true);
                });
                h2.appendChild(closeBtn);
            }
        }

        // Botão de recolher busca em #toolbar
        const toolbarForm = document.querySelector('#toolbar form');
        if (toolbarForm && !toolbarForm.querySelector('.btn-collapse-search-bar')) {
            const collapseBtn = document.createElement('button');
            collapseBtn.type = 'button';
            collapseBtn.className = 'btn-collapse-search-bar';
            collapseBtn.title = 'Recolher barra de busca (Alt+T)';
            collapseBtn.innerHTML = '▲';
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleTopFilter(true);
            });
            toolbarForm.appendChild(collapseBtn);
        }
    }

    /**
     * Configura ouvintes de eventos da barra superior e do dock
     */
    function setupEventListeners() {
        // Botões da Barra Superior
        const btnSidebar = document.getElementById('btn-toggle-left-sidebar');
        if (btnSidebar) btnSidebar.addEventListener('click', () => toggleLeftSidebar());

        const btnCloseSidebar = document.getElementById('btn-close-nav-sidebar');
        if (btnCloseSidebar) btnCloseSidebar.addEventListener('click', () => toggleLeftSidebar(true));

        const btnBreadcrumbs = document.getElementById('btn-toggle-breadcrumbs');
        if (btnBreadcrumbs) btnBreadcrumbs.addEventListener('click', () => toggleBreadcrumbs());

        const btnTopFilter = document.getElementById('btn-toggle-top-filter');
        if (btnTopFilter) btnTopFilter.addEventListener('click', () => toggleTopFilter());

        const btnRightFilter = document.getElementById('btn-toggle-right-filter');
        if (btnRightFilter) btnRightFilter.addEventListener('click', () => toggleRightFilter());

        // Botão de fechar painel de filtros (caso presente no template estático)
        const btnCloseFilter = document.querySelector('.btn-close-filter-pane');
        if (btnCloseFilter) btnCloseFilter.addEventListener('click', () => toggleRightFilter(true));

        const btnFocus = document.getElementById('btn-toggle-focus-mode');
        if (btnFocus) btnFocus.addEventListener('click', () => toggleZenMode());

        const btnReset = document.getElementById('btn-reset-view-layout');
        if (btnReset) btnReset.addEventListener('click', () => resetLayout());

        // Floating Dock Menu
        const dockTrigger = document.getElementById('floating-dock-trigger');
        const dockMenu = document.getElementById('floating-dock-menu');
        if (dockTrigger && dockMenu) {
            dockTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                dockMenu.classList.toggle('open');
            });

            document.addEventListener('click', (e) => {
                if (!dockMenu.contains(e.target) && !dockTrigger.contains(e.target)) {
                    dockMenu.classList.remove('open');
                }
            });
        }

        // Itens do Floating Dock
        const dockLeft = document.getElementById('dock-item-left-sidebar');
        if (dockLeft) dockLeft.addEventListener('click', () => toggleLeftSidebar());

        const dockBreadcrumbs = document.getElementById('dock-item-breadcrumbs');
        if (dockBreadcrumbs) dockBreadcrumbs.addEventListener('click', () => toggleBreadcrumbs());

        const dockTop = document.getElementById('dock-item-top-filter');
        if (dockTop) dockTop.addEventListener('click', () => toggleTopFilter());

        const dockRight = document.getElementById('dock-item-right-filter');
        if (dockRight) dockRight.addEventListener('click', () => toggleRightFilter());

        const dockFocus = document.getElementById('dock-item-focus-mode');
        if (dockFocus) dockFocus.addEventListener('click', () => toggleZenMode());

        const dockReset = document.getElementById('dock-item-reset-layout');
        if (dockReset) dockReset.addEventListener('click', () => resetLayout());

        // Atalhos de teclado (Alt + tecla)
        document.addEventListener('keydown', (e) => {
            // Ignora se estiver digitando em campos de formulário
            const targetTag = (e.target.tagName || '').toLowerCase();
            if (targetTag === 'input' || targetTag === 'textarea' || targetTag === 'select' || e.target.isContentEditable) {
                return;
            }

            if (e.altKey && !e.ctrlKey && !e.metaKey) {
                const key = e.key.toLowerCase();
                if (key === 'm') {
                    e.preventDefault();
                    toggleLeftSidebar();
                } else if (key === 'f') {
                    e.preventDefault();
                    toggleRightFilter();
                } else if (key === 't') {
                    e.preventDefault();
                    toggleTopFilter();
                } else if (key === 'b') {
                    e.preventDefault();
                    toggleBreadcrumbs();
                } else if (key === 'z') {
                    e.preventDefault();
                    toggleZenMode();
                } else if (key === 'r' || key === '0') {
                    e.preventDefault();
                    resetLayout();
                }
            }
        });
    }

    /**
     * Inicialização no carregamento do DOM
     */
    function init() {
        applyClasses();
        injectInlineCloseButtons();
        setupEventListeners();
        updateUIElements();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exporta API para uso global ou console
    window.ConviverAdminToggles = {
        state,
        toggleLeftSidebar,
        toggleRightFilter,
        toggleTopFilter,
        toggleBreadcrumbs,
        toggleZenMode,
        resetLayout
    };
})();

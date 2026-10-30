/**
 * ============================================================================
 * CONVIVER / MANAGERONTEC - DJANGO ADMIN LAYOUT TOGGLES
 * ============================================================================
 * Gerencia a visibilidade retrátil dos componentes do Django Admin:
 * 1. Menu lateral esquerdo de modelos (#nav-sidebar)
 * 2. Menu lateral direito de filtros (#changelist-filter)
 * 3. Menu superior de busca e filtros (#toolbar, #changelist-search)
 * 4. Breadcrumbs (migalhas de navegação)
 * 5. Painel de Indicadores (KPIs) e barra de filtros analítica
 *
 * Persiste preferências do usuário em localStorage e sincroniza com o Django.
 * Atalhos: Alt+M (menu) · Alt+B (breadcrumbs) · Alt+F (filtros da direita)
 * · Alt+T (filtros do topo) · Alt+K (indicadores) · Alt+R (restaurar).
 */

(function () {
    'use strict';

    /**
     * ACESSO SEGURO AO localStorage.
     *
     * Ler `localStorage.getItem(...)` direto pode LANÇAR exceção (modo
     * privado, cookies de terceiros bloqueados, iframe, política de
     * armazenamento do navegador). Como isso acontecia na criação do `state`,
     * o arquivo inteiro morria na primeira linha e NENHUM botão funcionava
     * (indicadores, filtros, setas). Aqui a falha vira “sem preferência”.
     */
    function lerStorage(chave, padrao) {
        try {
            const valor = window.localStorage.getItem(chave);
            return valor === null ? padrao : valor;
        } catch (e) {
            return padrao;
        }
    }

    function gravarStorage(chave, valor) {
        try {
            window.localStorage.setItem(chave, valor);
        } catch (e) {
            /* sem armazenamento disponível: o estado vale só nesta página */
        }
    }

    function removerStorage(chave) {
        try {
            window.localStorage.removeItem(chave);
        } catch (e) { /* idem */ }
    }

    // Chaves de armazenamento
    const STORAGE_KEYS = {
        LEFT_SIDEBAR: 'conviver_hide_left_sidebar',
        RIGHT_FILTER: 'conviver_hide_right_filter',
        TOP_FILTER: 'conviver_hide_top_filter',
        BREADCRUMBS: 'conviver_hide_breadcrumbs',
        DASHBOARD: 'conviver_hide_dashboard',
        FILTERS_PANEL: 'conviver_hide_filters_panel'
    };

    // Estado local
    const state = {
        hideLeftSidebar: lerStorage(STORAGE_KEYS.LEFT_SIDEBAR, 'false') === 'true',
        hideRightFilter: lerStorage(STORAGE_KEYS.RIGHT_FILTER, 'false') === 'true',
        hideTopFilter: lerStorage(STORAGE_KEYS.TOP_FILTER, 'false') === 'true',
        hideBreadcrumbs: lerStorage(STORAGE_KEYS.BREADCRUMBS, 'false') === 'true',
        // PAINÉIS DE TOPO (indicadores e filtros analíticos): a preferência
        // gravada manda; SEM preferência, começam RECOLHIDOS — eles ocupavam
        // ~900px e empurravam a tabela para fora da tela (AGENTS.md, item 10:
        // a tabela é a estrela; dashboard e filtros são painéis à mão).
        hideDashboard: lerStorage(STORAGE_KEYS.DASHBOARD, 'true') === 'true',
        hideFiltersPanel: lerStorage(STORAGE_KEYS.FILTERS_PANEL, 'true') === 'true'
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
        toggleClass('hide-dashboard', state.hideDashboard);
        toggleClass('hide-filters', state.hideFiltersPanel);
        updatePanelButtons();

        // Sincroniza com navSidebar nativo do Django se presente
        const main = document.getElementById('main');
        const navSidebar = document.getElementById('nav-sidebar');
        if (main && navSidebar) {
            if (state.hideLeftSidebar) {
                main.classList.remove('shifted');
                navSidebar.setAttribute('aria-expanded', 'false');
                gravarStorage('django.admin.navSidebarIsOpen', 'false');
            } else {
                main.classList.add('shifted');
                navSidebar.setAttribute('aria-expanded', 'true');
                gravarStorage('django.admin.navSidebarIsOpen', 'true');
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

        // 3. Filtro Superior (busca do Django + barra analítica)
        const hasTopFilter = !!(document.getElementById('toolbar')
            || document.getElementById('changelist-search')
            || document.getElementById('admin-top-filter-bar'));
        updateButtonState('btn-toggle-top-filter', 'dock-item-top-filter',
            state.hideTopFilter || state.hideFiltersPanel, 'Filtro Topo', hasTopFilter);

        // 3b. Painel de Indicadores (KPIs)
        const hasDashboard = !!document.getElementById('admin-kpi-panel');
        updateButtonState('btn-toggle-dashboard', null, state.hideDashboard,
            'Indicadores', hasDashboard);

        // 4. Filtros Direita
        const hasRightFilter = !!document.getElementById('changelist-filter');
        updateButtonState('btn-toggle-right-filter', 'dock-item-right-filter', state.hideRightFilter, 'Filtros', hasRightFilter);

        // Atualiza contagem de filtros ativos
        updateFilterBadge();

        // (O antigo "Modo Foco / Zen" foi removido: ele fazia exatamente o
        // que o botão Breadcrumbs já fazia.)
        updatePanelButtons();
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
        // O botão de INDICADORES só aparece onde existe o painel de KPIs.
        if (btnId === 'btn-toggle-dashboard') {
            const temPainel = !!document.getElementById('admin-kpi-panel');
            btn.style.display = temPainel ? '' : 'none';
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
     * O painel está VISÍVEL na tela agora? (fonte da verdade dos toggles)
     */
    function painelVisivel(id) {
        const el = document.getElementById(id);
        if (!el) return false;
        return getComputedStyle(el).display !== 'none';
    }

    /**
     * Funções de Toggle Individuais
     */
    function toggleLeftSidebar(forceState) {
        state.hideLeftSidebar = (forceState !== undefined) ? forceState : !state.hideLeftSidebar;
        gravarStorage(STORAGE_KEYS.LEFT_SIDEBAR, state.hideLeftSidebar);
        applyClasses();
        updateUIElements();
    }

    function toggleRightFilter(forceState) {
        state.hideRightFilter = (forceState !== undefined) ? forceState : !state.hideRightFilter;
        gravarStorage(STORAGE_KEYS.RIGHT_FILTER, state.hideRightFilter);
        applyClasses();
        updateUIElements();
    }

    function toggleTopFilter(forceState) {
        state.hideTopFilter = (forceState !== undefined) ? forceState : !state.hideTopFilter;
        gravarStorage(STORAGE_KEYS.TOP_FILTER, state.hideTopFilter);
        applyClasses();
        updateUIElements();
    }

    function toggleBreadcrumbs(forceState) {
        state.hideBreadcrumbs = (forceState !== undefined) ? forceState : !state.hideBreadcrumbs;
        gravarStorage(STORAGE_KEYS.BREADCRUMBS, state.hideBreadcrumbs);
        applyClasses();
        updateUIElements();
    }

    /** Dashboard (KPIs) — ocultar/exibir sem esconder a tabela. */
    function toggleDashboard(forceState) {
        state.hideDashboard = (forceState !== undefined) ? forceState : !state.hideDashboard;
        gravarStorage(STORAGE_KEYS.DASHBOARD, state.hideDashboard);
        applyClasses();
    }

    /** Painel de filtros (barra superior) — ocultar/exibir. */
    function toggleFiltersPanel(forceState) {
        state.hideFiltersPanel = (forceState !== undefined) ? forceState : !state.hideFiltersPanel;
        gravarStorage(STORAGE_KEYS.FILTERS_PANEL, state.hideFiltersPanel);
        applyClasses();
    }

    /**
     * Atualiza o rótulo dos botões de ocultar/exibir dos painéis.
     */
    function updatePanelButtons() {
        document.querySelectorAll('[data-panel-toggle]').forEach((btn) => {
            const alvo = btn.dataset.panelToggle;
            const oculto = alvo === 'dashboard' ? state.hideDashboard : state.hideFiltersPanel;
            btn.classList.toggle('is-hidden', oculto);
            btn.title = oculto ? 'Exibir o painel' : 'Ocultar o painel';
        });
    }



    /**
     * Restaura visualização padrão (tudo visível)
     */
    function resetLayout() {
        state.hideLeftSidebar = false;
        state.hideRightFilter = false;
        state.hideTopFilter = false;
        state.hideBreadcrumbs = false;
        state.hideDashboard = false;
        state.hideFiltersPanel = false;

        removerStorage(STORAGE_KEYS.LEFT_SIDEBAR);
        removerStorage(STORAGE_KEYS.RIGHT_FILTER);
        removerStorage(STORAGE_KEYS.TOP_FILTER);
        removerStorage(STORAGE_KEYS.BREADCRUMBS);
        removerStorage(STORAGE_KEYS.DASHBOARD);
        removerStorage(STORAGE_KEYS.FILTERS_PANEL);

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
        if (btnTopFilter) {
            btnTopFilter.addEventListener('click', () =>
                toggleFiltersPanel(painelVisivel('admin-top-filter-bar')));
        }

        const btnRightFilter = document.getElementById('btn-toggle-right-filter');
        if (btnRightFilter) btnRightFilter.addEventListener('click', () => toggleRightFilter());

        const btnDashboard = document.getElementById('btn-toggle-dashboard');
        if (btnDashboard) {
            btnDashboard.addEventListener('click', () =>
                toggleDashboard(painelVisivel('admin-kpi-panel')));
        }

        // Botão de fechar painel de filtros (caso presente no template estático)
        const btnCloseFilter = document.querySelector('.btn-close-filter-pane');
        if (btnCloseFilter) btnCloseFilter.addEventListener('click', () => toggleRightFilter(true));



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
        if (dockTop) dockTop.addEventListener('click', () => toggleFiltersPanel());

        const dockRight = document.getElementById('dock-item-right-filter');
        if (dockRight) dockRight.addEventListener('click', () => toggleRightFilter());



        const dockReset = document.getElementById('dock-item-reset-layout');
        if (dockReset) dockReset.addEventListener('click', () => resetLayout());

        // Botões de ocultar/exibir dos PAINÉIS (indicadores e filtros).
        document.querySelectorAll('[data-panel-toggle]').forEach((btn) => {
            btn.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                // Decide pela VISIBILIDADE REAL do painel, não pelo estado em
                // memória: se o HTML já veio recolhido (ou o estado ficou
                // dessincronizado), o clique sempre faz o que o usuário vê.
                const idPainel = btn.dataset.panelToggle === 'dashboard'
                    ? 'admin-kpi-panel' : 'admin-top-filter-bar';
                const painel = document.getElementById(idPainel);
                const visivel = painel
                    ? getComputedStyle(painel).display !== 'none'
                    : false;
                if (btn.dataset.panelToggle === 'dashboard') {
                    toggleDashboard(visivel);   // visível → esconde
                } else {
                    toggleFiltersPanel(visivel); // visível → esconde
                }
            });
        });

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
                } else if (key === 'k') {
                    e.preventDefault();
                    toggleDashboard(painelVisivel('admin-kpi-panel'));
                } else if (key === 'f') {
                    e.preventDefault();
                    toggleRightFilter();
                } else if (key === 't') {
                    e.preventDefault();
                    toggleFiltersPanel(painelVisivel('admin-top-filter-bar'));
                } else if (key === 'b') {
                    e.preventDefault();
                    toggleBreadcrumbs();
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
        toggleDashboard,
        toggleFiltersPanel,
        resetLayout
    };
})();

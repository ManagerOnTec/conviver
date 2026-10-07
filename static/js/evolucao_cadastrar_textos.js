function decodeHtmlEntities(value) {
    const parser = new DOMParser();
    return parser.parseFromString(value ?? '', 'text/html').documentElement.textContent || '';
}

function normalizeEditorHtml(html) {
    return (html || '').replace(/<p><\/p>/g, '');
}

function getEvolutionEditor() {
    return tinymce.get('id_evolucao') || tinymce.get('evolucao');
}

function insertHtmlIntoEvolution(html, { prepend = false } = {}) {
    const editor = getEvolutionEditor();
    if (!editor) {
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

// Inserir texto com diagnósticos, garantindo que o diagnóstico fique acima do texto existente
document.addEventListener('DOMContentLoaded', function () {
    const btnBuscarDiagnosticos = document.getElementById('btn-buscar-diagnosticos');

    btnBuscarDiagnosticos.addEventListener('click', function () {
        const atendimentoId = this.getAttribute('data-atendimento-id');
        const url = `/prontuarios/buscar_diagnosticos/${atendimentoId}/`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                const diagnosticosTexto = data.diagnosticos.join(', ');
                insertHtmlIntoEvolution(diagnosticosTexto, { prepend: true });
            })
            .catch(error => console.error('Erro ao buscar diagnósticos:', error));
    });
});



document.addEventListener('DOMContentLoaded', function () {
    // Atribuição do evento de clique para o botão 'Texto Padrão'
    const button = document.getElementById('insertDefaultText');
    button.addEventListener('click', function (event) {
        event.preventDefault(); // Previne a ação padrão
        showContextMenu(event); // Chama a função showContextMenu
    });

    // Fechar o menu ao clicar fora
    document.addEventListener('click', function (event) {
        const contextMenu = document.getElementById('context-menu');
        if (!button.contains(event.target)) { // Se o clique foi fora do botão 'Texto Padrão'
            contextMenu.style.display = 'none';
        }
    });
});

// Função para exibir o menu de contexto
function showContextMenu(event) {
    const contextMenu = document.getElementById('context-menu');
    contextMenu.style.display = 'block';
    const menuWidth = contextMenu.offsetWidth; // Largura do menu
    let posX = event.clientX - menuWidth;
    if (posX < 0) {
        posX = event.clientX; // Ajusta a posição X para não ultrapassar a tela
    }
    contextMenu.style.left = `${posX}px`;
    contextMenu.style.top = `${event.clientY}px`;
    contextMenu.style.display = 'block';

    getTextosPadraoFiltrados()
        .then(data => {
            const ul = document.createElement('ul');
            const li = document.createElement('li');
            li.textContent = 'Evoluções Padronizadas';
            li.classList.add('has-submenu');
            const submenu = document.createElement('ul');
            submenu.classList.add('submenu');

            data.forEach(item => {
                const subLi = document.createElement('li');
                let descricao = item.descricao;
                descricao += item.tipo_evolucao__tipo_evolucao ? ` - Tipo de evolução: ${item.tipo_evolucao__tipo_evolucao}` : '';
                descricao += item.profissao__profissao ? ` - Profissão: ${item.profissao__profissao}` : '';
                descricao += item.profissional__profissional ? ` - Profissional: ${item.profissional__profissional}` : '';
                subLi.textContent = descricao;
                subLi.addEventListener('click', function () {
                    insertHtmlIntoEvolution(item.texto);
                    contextMenu.style.display = 'none'; // Esconde o menu
                });

                submenu.appendChild(subLi);
            });

            li.appendChild(submenu);
            ul.appendChild(li);

            contextMenu.innerHTML = ''; // Limpa o menu atual antes de adicionar novos itens
            contextMenu.appendChild(ul);
        })
        .catch(error => {
            console.error('Erro ao obter textos padrão filtrados:', error);
            alert("Erro ao buscar os textos padrões. Tente novamente.");
        });
}


function getTextosPadraoFiltrados() {
    return new Promise((resolve, reject) => {
        const url = '/prontuarios/textopadrao_filtrado/';

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => resolve(data))
            .catch(error => {
                console.error('Erro ao obter textos padrão filtrados:', error);
                reject(error);
            });
    });
}

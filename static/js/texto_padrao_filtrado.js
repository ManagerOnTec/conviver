function getDocumentEditor() {
    const editorIds = ['id_ata', 'ata', 'id_oficio', 'oficio', 'id_orcamento', 'orcamento'];

    for (const editorId of editorIds) {
        const editor = tinymce.get(editorId);
        if (editor) {
            return editor;
        }
    }

    return null;
}

function parseDocumentHtml(html) {
    const parser = new DOMParser();
    return parser.parseFromString(html ?? '', 'text/html').body.innerHTML;
}

function insertHtmlIntoDocument(html) {
    const editor = getDocumentEditor();
    if (!editor) {
        return;
    }

    const parsedHtml = parseDocumentHtml(html).trim();
    if (!parsedHtml) {
        return;
    }

    const currentContent = editor.getContent({ format: 'html' }).trim();
    const emptyContent = ['', '<p></p>', '<p><br data-mce-bogus="1"></p>', '<p>&nbsp;</p>'];

    if (emptyContent.includes(currentContent)) {
        editor.setContent(parsedHtml);
    } else {
        editor.setContent(`${currentContent}${parsedHtml}`);
    }

    editor.save();
    editor.focus();
}

document.addEventListener('DOMContentLoaded', function () {
    const button = document.getElementById('insertDefaultDocs');
    const contextMenu = document.getElementById('context-menu');

    if (!button || !contextMenu) {
        return;
    }

    button.addEventListener('click', function (event) {
        event.preventDefault();
        showContextMenu(event, button.dataset.tipoDocumento);
    });

    document.addEventListener('click', function (event) {
        if (!button.contains(event.target) && !contextMenu.contains(event.target)) {
            contextMenu.style.display = 'none';
        }
    });
});

function showContextMenu(event, tipoDocumento) {
    const contextMenu = document.getElementById('context-menu');
    contextMenu.style.display = 'block';

    const menuWidth = contextMenu.offsetWidth;
    let posX = event.clientX - menuWidth;
    if (posX < 0) {
        posX = event.clientX;
    }

    contextMenu.style.left = `${posX}px`;
    contextMenu.style.top = `${event.clientY}px`;

    getTextosPadraoPorTipo(tipoDocumento)
        .then(data => {
            const ul = document.createElement('ul');

            data.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item.descricao;
                li.addEventListener('click', function () {
                    insertHtmlIntoDocument(item.texto);
                    contextMenu.style.display = 'none';
                });
                ul.appendChild(li);
            });

            contextMenu.innerHTML = '';
            contextMenu.appendChild(ul);
        })
        .catch(error => {
            console.error('Erro ao obter textos padrão dos documentos:', error);
            alert('Erro ao buscar os textos padrões. Tente novamente.');
        });
}

function getTextosPadraoPorTipo(tipoDocumento) {
    return fetch(`/texto-padrao/${tipoDocumento}/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            return response.json();
        });
}
(function () {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function isImageFile(fileName) {
        return /\.(jpg|jpeg|png)$/i.test(fileName || '');
    }

    function buildImagePreview(src, fileName) {
        return `
            <div>
                <img
                    src="${src}"
                    alt="${escapeHtml(fileName)}"
                    class="img-fluid img-thumbnail shadow-sm"
                    style="max-width: 220px; max-height: 220px; object-fit: contain;"
                />
                <div class="small text-muted mt-2">${escapeHtml(fileName)}</div>
            </div>
        `;
    }

    function buildDocumentPreview(fileName) {
        return `
            <div class="small text-muted">
                Arquivo selecionado: <strong>${escapeHtml(fileName)}</strong>
            </div>
        `;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const inputs = document.querySelectorAll('input[type="file"][data-attachment-preview-target]');

        inputs.forEach(function (input) {
            const previewId = input.dataset.attachmentPreviewTarget;
            const previewContainer = previewId ? document.getElementById(previewId) : null;

            if (!previewContainer) {
                return;
            }

            input.addEventListener('change', function () {
                const file = input.files && input.files[0];
                if (!file) {
                    return;
                }

                if (!isImageFile(file.name)) {
                    previewContainer.innerHTML = buildDocumentPreview(file.name);
                    return;
                }

                const reader = new FileReader();
                reader.onload = function (event) {
                    previewContainer.innerHTML = buildImagePreview(event.target.result, file.name);
                };
                reader.readAsDataURL(file);
            });
        });
    });
})();
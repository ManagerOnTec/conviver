function initSignaturePad() {
    const canvas = document.getElementById('signature-pad');
    const hiddenInput = document.getElementById('id_assinatura_data');
    const clearButton = document.getElementById('clear-signature');

    if (!canvas || !hiddenInput) {
        return;
    }

    const context = canvas.getContext('2d');
    let drawing = false;

    function restoreSignatureFromHiddenInput() {
        if (!hiddenInput.value || !hiddenInput.value.startsWith('data:image/')) {
            return;
        }

        const image = new Image();
        image.onload = function () {
            const rect = canvas.getBoundingClientRect();
            configureContext(rect.width);
            context.drawImage(image, 0, 0, rect.width, 220);
        };
        image.src = hiddenInput.value;
    }

    function configureContext(width) {
        context.lineWidth = 2;
        context.lineCap = 'round';
        context.lineJoin = 'round';
        context.strokeStyle = '#111';
        context.fillStyle = '#fff';
        context.fillRect(0, 0, width, 220);
    }

    function resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * ratio;
        canvas.height = 220 * ratio;
        context.setTransform(1, 0, 0, 1, 0, 0);
        context.scale(ratio, ratio);
        configureContext(rect.width);
        restoreSignatureFromHiddenInput();
    }

    function getPoint(event) {
        const rect = canvas.getBoundingClientRect();
        const clientX = event.touches ? event.touches[0].clientX : event.clientX;
        const clientY = event.touches ? event.touches[0].clientY : event.clientY;
        return { x: clientX - rect.left, y: clientY - rect.top };
    }

    function saveSignature() {
        hiddenInput.value = canvas.toDataURL('image/png');
    }

    function startDrawing(event) {
        drawing = true;
        const point = getPoint(event);
        context.beginPath();
        context.moveTo(point.x, point.y);
        event.preventDefault();
    }

    function draw(event) {
        if (!drawing) {
            return;
        }
        const point = getPoint(event);
        context.lineTo(point.x, point.y);
        context.stroke();
        saveSignature();
        event.preventDefault();
    }

    function stopDrawing() {
        drawing = false;
    }

    clearButton?.addEventListener('click', function () {
        resizeCanvas();
        hiddenInput.value = '';
    });

    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseleave', stopDrawing);
    canvas.addEventListener('touchstart', startDrawing, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', stopDrawing);
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
}

function initCameraCapture() {
    const video = document.getElementById('camera-stream');
    const canvas = document.getElementById('camera-canvas');
    const preview = document.getElementById('camera-preview');
    const hiddenInput = document.getElementById('id_foto_validacao_data');
    const startButton = document.getElementById('start-camera');
    const captureButton = document.getElementById('capture-photo');
    const resetButton = document.getElementById('reset-photo');
    const feedback = document.getElementById('camera-feedback');

    if (!video || !canvas || !preview || !hiddenInput) {
        return;
    }

    let stream = null;

    function stopCameraStream() {
        if (stream) {
            stream.getTracks().forEach(function (track) {
                track.stop();
            });
            stream = null;
        }
    }

    function setFeedback(message, isError = false) {
        feedback.textContent = message;
        feedback.classList.toggle('text-danger', isError);
    }

    function restoreSavedPhoto() {
        if (!hiddenInput.value || !hiddenInput.value.startsWith('data:image/')) {
            return;
        }

        preview.src = hiddenInput.value;
        preview.classList.remove('d-none');
        setFeedback('Foto reaproveitada após a validação. Capture novamente se quiser substituir.');
    }

    async function startCamera(event) {
        event?.preventDefault();
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setFeedback('Este navegador não suporta captura de câmera.', true);
            return;
        }

        try {
            stopCameraStream();
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false,
            });
            video.srcObject = stream;
            await video.play();
            captureButton.disabled = false;
            setFeedback('Câmera ativa. Capture a foto quando o enquadramento estiver correto.');
        } catch (error) {
            captureButton.disabled = true;
            setFeedback('Não foi possível acessar a câmera. Verifique a permissão do navegador e tente novamente.', true);
        }
    }

    function capturePhoto(event) {
        event?.preventDefault();
        if (!video.videoWidth || !video.videoHeight) {
            setFeedback('Ative a câmera antes de capturar a foto.', true);
            return;
        }

        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const dataUrl = canvas.toDataURL('image/png');
        hiddenInput.value = dataUrl;
        preview.src = dataUrl;
        preview.classList.remove('d-none');
        setFeedback('Foto capturada com sucesso. Se necessário, capture novamente antes de salvar.');
    }

    function resetPhoto(event) {
        event?.preventDefault();
        hiddenInput.value = '';
        preview.src = '';
        preview.classList.add('d-none');
        captureButton.disabled = !stream;
        setFeedback('Nenhuma foto capturada ainda.');
    }

    startButton?.addEventListener('click', startCamera);
    captureButton?.addEventListener('click', capturePhoto);
    resetButton?.addEventListener('click', resetPhoto);
    restoreSavedPhoto();

    window.addEventListener('beforeunload', function () {
        stopCameraStream();
    });
}

function initTemplatePreview() {
    const root = document.getElementById('documento-legal-root');
    const tipoSelect = document.getElementById('id_tipo_documento');
    const modeloSelect = document.getElementById('id_modelo_documento');
    const preview = document.getElementById('documento-preview');

    if (!root || !tipoSelect || !modeloSelect || !preview) {
        return;
    }

    function populateModelOptions(modelos, selectedId) {
        modeloSelect.innerHTML = '<option value="">---------</option>';
        modelos.forEach(function (modelo) {
            const option = document.createElement('option');
            option.value = modelo.id;
            option.textContent = modelo.nome;
            if (String(modelo.id) === String(selectedId)) {
                option.selected = true;
            }
            modeloSelect.appendChild(option);
        });
    }

    function loadPreview() {
        const tipoId = tipoSelect.value;
        const modeloId = modeloSelect.value;
        if (!tipoId) {
            preview.innerHTML = '<p class="text-muted">Selecione um tipo de termo para carregar a prévia.</p>';
            modeloSelect.innerHTML = '<option value="">---------</option>';
            return;
        }

        const url = `${root.dataset.previewUrl}?tipo_id=${encodeURIComponent(tipoId)}&modelo_id=${encodeURIComponent(modeloId || '')}`;
        fetch(url)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Falha ao carregar o modelo do termo.');
                }
                return response.json();
            })
            .then(function (data) {
                populateModelOptions(data.modelos || [], data.modelo_id);
                preview.innerHTML = data.html || '<p class="text-muted">Nenhum conteúdo disponível.</p>';
            })
            .catch(function (error) {
                preview.innerHTML = `<p class="text-danger">${error.message}</p>`;
            });
    }

    tipoSelect.addEventListener('change', function () {
        modeloSelect.value = '';
        loadPreview();
    });
    modeloSelect.addEventListener('change', loadPreview);

    if (tipoSelect.value) {
        loadPreview();
    } else {
        preview.innerHTML = '<p class="text-muted">Selecione um tipo de termo para carregar a prévia.</p>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    initSignaturePad();
    initCameraCapture();
    initTemplatePreview();
});

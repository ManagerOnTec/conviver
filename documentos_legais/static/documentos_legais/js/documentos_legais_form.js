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

// Câmera compartilhada entre as duas capturas (responsável e documento).
// A webcam do notebook normalmente aceita apenas UMA stream ativa por vez. Para não
// travar a segunda captura enquanto a primeira está aberta, a foto do documento só
// pode ser ativada depois que a foto do responsável for capturada, e a stream é
// liberada (tracks encerradas + srcObject limpo) ao capturar.
const sharedCamera = {
    stream: null,
    video: null,
};

function releaseSharedCamera() {
    if (sharedCamera.stream) {
        sharedCamera.stream.getTracks().forEach(function (track) {
            track.stop();
        });
        sharedCamera.stream = null;
    }
    if (sharedCamera.video) {
        try {
            sharedCamera.video.pause();
        } catch (error) {
            // ignora: vídeo pode não estar em reprodução
        }
        sharedCamera.video.srcObject = null;
        sharedCamera.video = null;
    }
}

function initCameraCapture(options) {
    const config = options || {};
    const video = document.getElementById(config.videoId);
    const canvas = document.getElementById(config.canvasId);
    const preview = document.getElementById(config.previewId);
    const hiddenInput = document.getElementById(config.inputId);
    const startButton = document.getElementById(config.startButtonId);
    const captureButton = document.getElementById(config.captureButtonId);
    const resetButton = document.getElementById(config.resetButtonId);
    const feedback = document.getElementById(config.feedbackId);

    if (!video || !canvas || !preview || !hiddenInput) {
        return;
    }

    let cameraReady = false;

    function setFeedback(message, isError = false) {
        if (!feedback) {
            return;
        }
        feedback.textContent = message;
        feedback.classList.toggle('text-danger', isError);
    }

    function stopLocalStream() {
        if (sharedCamera.video === video) {
            releaseSharedCamera();
        } else if (video.srcObject) {
            video.srcObject.getTracks().forEach(function (track) {
                track.stop();
            });
            video.srcObject = null;
        }
        cameraReady = false;
        if (captureButton) {
            captureButton.disabled = true;
        }
    }

    function restoreSavedPhoto() {
        if (!hiddenInput.value || !hiddenInput.value.startsWith('data:image/')) {
            return;
        }

        preview.src = hiddenInput.value;
        preview.classList.remove('d-none');
        setFeedback('Foto reaproveitada após a validação. Capture novamente se quiser substituir.');
    }

    function handleStreamReady() {
        if (sharedCamera.video !== video) {
            return;
        }
        cameraReady = true;
        if (captureButton) {
            captureButton.disabled = false;
        }
        setFeedback('Câmera ativa. Capture a foto quando o enquadramento estiver correto.');
    }

    function bindVideoReadyHandler() {
        if (video.readyState >= 2 && video.videoWidth > 0) {
            handleStreamReady();
            return;
        }

        video.onloadedmetadata = function () {
            handleStreamReady();
        };
    }

    async function startCamera(event) {
        event?.preventDefault();

        // Pré-validador: cada captura pode exigir que a anterior esteja concluída.
        if (typeof config.canActivate === 'function' && !config.canActivate()) {
            setFeedback(config.blockedMessage || 'Conclua a captura anterior antes de ativar esta câmera.', true);
            return;
        }

        setFeedback('Preparando câmera...');
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setFeedback('Este navegador não suporta captura de câmera.', true);
            return;
        }

        try {
            // Garante que nenhuma outra captura esteja segurando o dispositivo físico.
            releaseSharedCamera();
            stopLocalStream();
            setFeedback('Solicitando acesso à câmera do notebook...');

            const constraintsList = [
                {
                    video: {
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        facingMode: { ideal: config.facingMode || 'user' },
                    },
                    audio: false,
                },
                {
                    video: {
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                    },
                    audio: false,
                },
                { video: true, audio: false },
            ];

            let stream = null;
            let lastError = null;
            for (const constraints of constraintsList) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                    break;
                } catch (error) {
                    lastError = error;
                }
            }

            if (!stream) {
                throw lastError || new Error('Nenhuma câmera compatível foi encontrada.');
            }

            sharedCamera.stream = stream;
            sharedCamera.video = video;

            video.setAttribute('autoplay', 'true');
            video.setAttribute('playsinline', 'true');
            video.muted = true;
            video.srcObject = stream;
            if (captureButton) {
                captureButton.disabled = false;
            }
            try {
                await video.play();
            } catch (playError) {
                // Alguns navegadores rejeitam play() mesmo com o stream ligado; a
                // imagem costuma aparecer mesmo assim, então não tratamos como falha.
            }
            bindVideoReadyHandler();
        } catch (error) {
            stopLocalStream();
            setFeedback('Não foi possível acessar a câmera. Verifique a permissão do navegador, feche outros apps que estejam usando a webcam e tente novamente.', true);
        }
    }

    function capturePhoto(event) {
        event?.preventDefault();
        if (!cameraReady || !video.videoWidth || !video.videoHeight) {
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

        // Libera a câmera física para a próxima captura e notifica o formulário.
        stopLocalStream();
        setFeedback('Foto capturada com sucesso. Agora ative a câmera do documento, se necessário.');
        if (typeof config.onCaptured === 'function') {
            config.onCaptured();
        }
    }

    function resetPhoto(event) {
        event?.preventDefault();
        hiddenInput.value = '';
        preview.src = '';
        preview.classList.add('d-none');
        if (captureButton) {
            captureButton.disabled = true;
        }
        setFeedback('Nenhuma foto capturada ainda.');
        if (typeof config.onReset === 'function') {
            config.onReset();
        }
    }

    startButton?.addEventListener('click', startCamera);
    captureButton?.addEventListener('click', capturePhoto);
    resetButton?.addEventListener('click', resetPhoto);
    restoreSavedPhoto();

    window.addEventListener('beforeunload', function () {
        stopLocalStream();
    });
}

function initCameras() {
    const startDocumentoButton = document.getElementById('start-documento-camera');
    const captureDocumentoButton = document.getElementById('capture-documento');
    const documentoFeedback = document.getElementById('documento-feedback');
    const fotoResponsavelInput = document.getElementById('id_foto_validacao_data');

    // Pré-validador: a câmera do documento só é habilitada depois que a foto do
    // responsável foi capturada com sucesso.
    function responsavelFotoCapturada() {
        return Boolean(fotoResponsavelInput && fotoResponsavelInput.value);
    }

    function atualizarGatingDocumento() {
        const liberado = responsavelFotoCapturada();
        if (startDocumentoButton) {
            startDocumentoButton.disabled = !liberado;
            startDocumentoButton.title = liberado
                ? ''
                : 'Capture primeiro a foto do responsável para liberar a câmera do documento.';
        }
        if (!liberado && captureDocumentoButton) {
            captureDocumentoButton.disabled = true;
        }
        if (documentoFeedback) {
            if (liberado) {
                if (documentoFeedback.dataset.blocked === 'true') {
                    documentoFeedback.dataset.blocked = 'false';
                    documentoFeedback.classList.remove('text-danger');
                    documentoFeedback.textContent = 'Câmera do documento liberada. Clique em "Ativar câmera" para capturar.';
                }
            } else {
                documentoFeedback.dataset.blocked = 'true';
                documentoFeedback.textContent = 'Capture primeiro a foto do responsável para liberar a câmera do documento.';
            }
        }
    }

    initCameraCapture({
        videoId: 'camera-stream',
        canvasId: 'camera-canvas',
        previewId: 'camera-preview',
        inputId: 'id_foto_validacao_data',
        startButtonId: 'start-camera',
        captureButtonId: 'capture-photo',
        resetButtonId: 'reset-photo',
        feedbackId: 'camera-feedback',
        onCaptured: atualizarGatingDocumento,
        onReset: atualizarGatingDocumento,
    });

    initCameraCapture({
        videoId: 'documento-stream',
        canvasId: 'documento-canvas',
        previewId: 'documento-preview',
        inputId: 'id_foto_documento_data',
        startButtonId: 'start-documento-camera',
        captureButtonId: 'capture-documento',
        resetButtonId: 'reset-documento',
        feedbackId: 'documento-feedback',
        canActivate: responsavelFotoCapturada,
        blockedMessage: 'Capture primeiro a foto do responsável para liberar a câmera do documento.',
    });

    atualizarGatingDocumento();
}

const CAMPOS_RESPONSAVEL = [
    'id_responsavel_nome',
    'id_responsavel_cpf',
    'id_responsavel_documento',
    'id_responsavel_data_nascimento',
];

function toggleRequiredBlocks(modelo) {
    const blocoResponsavel = document.getElementById('bloco-assinatura-responsavel');
    const blocoFotos = document.getElementById('bloco-fotos-validacao');
    const blocoAtendente = document.getElementById('bloco-assinatura-atendente');
    const blocoDadosResponsavel = document.getElementById('bloco-dados-responsavel');
    const badgeResponsavel = document.getElementById('bloco-dados-responsavel-badge');
    const noteResponsavel = document.getElementById('bloco-dados-responsavel-note');
    const assinarFuncionario = document.getElementById('id_assinar_funcionario');

    const exigeResponsavel = modelo ? modelo.exige_assinatura_responsavel !== false : true;
    const exigeAtendente = modelo ? modelo.exige_assinatura_atendente !== false : true;

    if (blocoResponsavel) {
        blocoResponsavel.hidden = !exigeResponsavel;
        blocoResponsavel.style.display = exigeResponsavel ? '' : 'none';
    }
    if (blocoFotos) {
        blocoFotos.hidden = !exigeResponsavel;
        blocoFotos.style.display = exigeResponsavel ? '' : 'none';
    }
    if (blocoAtendente) {
        blocoAtendente.hidden = !exigeAtendente;
        blocoAtendente.style.display = exigeAtendente ? '' : 'none';
    }

    // O bloco de dados do responsável permanece visível, mas quando o modelo não exige a
    // assinatura dele os campos ficam opcionais e recebem destaque informando isso.
    if (blocoDadosResponsavel) {
        blocoDadosResponsavel.classList.toggle('is-opcional', !exigeResponsavel);
    }
    if (badgeResponsavel) {
        badgeResponsavel.textContent = exigeResponsavel ? 'Obrigatório' : 'Opcional';
        badgeResponsavel.classList.toggle('text-bg-secondary', exigeResponsavel);
        badgeResponsavel.classList.toggle('text-bg-warning', !exigeResponsavel);
    }
    if (noteResponsavel) {
        noteResponsavel.classList.toggle('d-none', exigeResponsavel);
    }

    // Quando o modelo não exige a assinatura do responsável, os campos de dados dele
    // deixam de ser obrigatórios também no navegador (remove o atributo required), para
    // não bloquear o envio do formulário.
    CAMPOS_RESPONSAVEL.forEach(function (campoId) {
        const campo = document.getElementById(campoId);
        if (!campo) {
            return;
        }
        if (exigeResponsavel) {
            campo.setAttribute('required', 'required');
        } else {
            campo.removeAttribute('required');
        }
    });

    // Quando o modelo não exige assinatura do atendente, desmarca a opção de assinatura
    // digital do funcionário para que o termo seja gerado sem ela.
    if (assinarFuncionario) {
        if (!exigeAtendente) {
            assinarFuncionario.checked = false;
            assinarFuncionario.disabled = true;
        } else {
            assinarFuncionario.disabled = false;
        }
    }
}

function initTemplatePreview() {
    const root = document.getElementById('documento-legal-root');
    const tipoSelect = document.getElementById('id_tipo_documento');
    const modeloSelect = document.getElementById('id_modelo_documento');
    const abrirModalButton = document.getElementById('abrir-termo-modal');
    const modalElement = document.getElementById('termo-modal');
    const modalContent = document.getElementById('termo-modal-content');
    const modalAceite = document.getElementById('termo-modal-aceite');
    const modalConfirmar = document.getElementById('termo-modal-confirmar');
    const declaracaoAceite = document.getElementById('id_declaracao_aceite');
    const aceiteHint = document.getElementById('declaracao-aceite-hint');

    if (!root || !tipoSelect || !modeloSelect || root.dataset.previewInitialized === 'true') {
        return;
    }
    root.dataset.previewInitialized = 'true';

    // O modal fica dentro de #right-content, que é position:fixed com overflow:auto.
    // Bootstrap posiciona o modal e o backdrop em relação ao viewport, e um ancestral
    // fixo/rolável pode prender/clipar o backdrop, deixando o modal sem cliques. Movemos
    // o modal para o <body> para garantir o comportamento correto.
    if (modalElement && modalElement.parentElement !== document.body) {
        document.body.appendChild(modalElement);
    }

    // O modal do Bootstrap pode ainda não estar disponível dependendo da ordem de
    // carregamento dos scripts. Resolvemos a instância de forma tardia para não depender
    // disso no momento da inicialização.
    let modalInstance = null;
    function getModalInstance() {
        if (modalInstance) {
            return modalInstance;
        }
        if (!modalElement || !window.bootstrap || !window.bootstrap.Modal) {
            return null;
        }
        modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalElement);
        return modalInstance;
    }

    function abrirModalTermo() {
        const instance = getModalInstance();
        if (instance) {
            instance.show();
            return true;
        }
        // Fallback: se o bundle do Bootstrap não carregou, exibe o modal manualmente
        // (classe .show + backdrop), garantindo que os botões continuem clicáveis.
        if (modalElement) {
            modalElement.classList.add('show');
            modalElement.style.display = 'block';
            modalElement.removeAttribute('aria-hidden');
        }
        return false;
    }

    function fecharModalTermo() {
        const instance = getModalInstance();
        if (instance) {
            instance.hide();
            return;
        }
        if (modalElement) {
            modalElement.classList.remove('show');
            modalElement.style.display = 'none';
        }
    }

    // Guarda a leitura confirmada: precisa bater com o modelo atualmente selecionado.
    // Quando o formulário volta com erro já aceito, preservamos a confirmação.
    let modeloConfirmadoId = (declaracaoAceite && declaracaoAceite.checked && modeloSelect.value)
        ? modeloSelect.value
        : null;
    let htmlAtual = '';

    function modeloSelecionadoId() {
        return modeloSelect.value || null;
    }

    function setFeedbackAceite(mensagem, tipo) {
        if (!aceiteHint) {
            return;
        }
        aceiteHint.textContent = mensagem;
        aceiteHint.classList.remove('text-muted', 'text-success', 'text-danger');
        aceiteHint.classList.add(tipo || 'text-muted');
    }

    function atualizarEstadoAceite() {
        const selecionado = modeloSelecionadoId();
        const confirmado = Boolean(selecionado) && selecionado === modeloConfirmadoId;

        if (declaracaoAceite && !declaracaoAceite.checked && confirmado) {
            declaracaoAceite.checked = true;
        }
        if (declaracaoAceite && !confirmado) {
            declaracaoAceite.checked = false;
        }

        if (abrirModalButton) {
            abrirModalButton.disabled = !selecionado;
        }

        if (confirmado) {
            setFeedbackAceite('Termo lido e confirmado. O salvamento está liberado.', 'text-success');
        } else if (selecionado) {
            setFeedbackAceite('Abra o termo no botão "Ler termo" e confirme a leitura para habilitar o salvamento.', 'text-muted');
        } else {
            setFeedbackAceite('Selecione um tipo e um modelo para habilitar a leitura do termo.', 'text-muted');
        }
    }

    function renderModal(html) {
        htmlAtual = html || '';
        if (modalContent) {
            modalContent.innerHTML = htmlAtual || '<p class="text-muted">Nenhum conteúdo disponível para este modelo.</p>';
        }
        if (modalAceite) {
            modalAceite.checked = false;
        }
        if (modalConfirmar) {
            modalConfirmar.disabled = true;
        }
    }

    function populateModelOptions(modelos, selectedId) {
        modeloSelect.innerHTML = '<option value="">---------</option>';
        modelos.forEach(function (modelo) {
            const option = document.createElement('option');
            option.value = modelo.id;
            option.textContent = modelo.nome;
            option.dataset.exigeResponsavel = modelo.exige_assinatura_responsavel === false ? 'false' : 'true';
            option.dataset.exigeAtendente = modelo.exige_assinatura_atendente === false ? 'false' : 'true';
            if (String(modelo.id) === String(selectedId)) {
                option.selected = true;
            }
            modeloSelect.appendChild(option);
        });
    }

    function applyModeloFlags(modelos, modeloId) {
        const modelo = (modelos || []).find(function (item) {
            return String(item.id) === String(modeloId);
        });
        toggleRequiredBlocks(modelo || null);
    }

    function carregarTermo(abrirModal) {
        const tipoId = tipoSelect.value;
        const modeloId = modeloSelect.value;

        if (!tipoId) {
            modeloConfirmadoId = null;
            modeloSelect.innerHTML = '<option value="">---------</option>';
            toggleRequiredBlocks(null);
            renderModal('');
            atualizarEstadoAceite();
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

                // A opção efetivamente selecionada após popular pode ser diferente da
                // que veio na URL (ex.: nenhum modelo escolhido). Se mudou em relação
                // à leitura confirmada, invalida a confirmação.
                const modeloSelecionado = modeloSelect.value || null;
                if (modeloSelecionado !== modeloConfirmadoId) {
                    modeloConfirmadoId = null;
                }

                applyModeloFlags(data.modelos || [], data.modelo_id || modeloSelect.value);

                // Não sobrescreve o conteúdo já confirmado do mesmo modelo.
                if (!(modeloSelecionado && modeloSelecionado === modeloConfirmadoId)) {
                    renderModal(data.html || '');
                }

                // Só abre automaticamente quando o usuário escolheu um modelo específico.
                if (abrirModal && modeloSelect.value) {
                    abrirModalTermo();
                }
                atualizarEstadoAceite();
            })
            .catch(function (error) {
                if (modalContent) {
                    modalContent.innerHTML = `<p class="text-danger">${error.message}</p>`;
                }
            });
    }

    abrirModalButton?.addEventListener('click', function () {
        if (!modeloSelect.value) {
            return;
        }
        abrirModalTermo();
    });

    // O atalho do menu lateral abre o mesmo modal de leitura.
    const menuLerTermo = document.getElementById('menu-ler-termo');
    menuLerTermo?.addEventListener('click', function () {
        abrirModalTermo();
    });

    modalAceite?.addEventListener('change', function () {
        if (modalConfirmar) {
            modalConfirmar.disabled = !modalAceite.checked;
        }
    });

    modalConfirmar?.addEventListener('click', function () {
        const selecionado = modeloSelecionadoId();
        if (!selecionado) {
            return;
        }
        modeloConfirmadoId = selecionado;
        atualizarEstadoAceite();
        fecharModalTermo();
    });

    tipoSelect.addEventListener('change', function () {
        modeloSelect.value = '';
        modeloConfirmadoId = null;
        carregarTermo(false);
    });

    modeloSelect.addEventListener('change', function () {
        const selectedOption = modeloSelect.options[modeloSelect.selectedIndex];
        if (selectedOption && selectedOption.value) {
            toggleRequiredBlocks({
                exige_assinatura_responsavel: selectedOption.dataset.exigeResponsavel !== 'false',
                exige_assinatura_atendente: selectedOption.dataset.exigeAtendente !== 'false',
            });
        }
        carregarTermo(true);
    });

    // Impede o envio enquanto o termo não tiver leitura confirmada.
    const form = document.getElementById('form-documento-legal');
    form?.addEventListener('submit', function (event) {
        const selecionado = modeloSelecionadoId();
        if (!selecionado || selecionado !== modeloConfirmadoId) {
            event.preventDefault();
            abrirModalTermo();
            setFeedbackAceite('Leia o termo e confirme a leitura antes de salvar.', 'text-danger');
        }
    });

    if (tipoSelect.value) {
        carregarTermo(false);
    } else {
        toggleRequiredBlocks(null);
    }

    atualizarEstadoAceite();
}

function bootDocumentoLegalForm() {
    initSignaturePad();
    initCameras();
    initTemplatePreview();
}

let documentoLegalFormBooted = false;
function bootDocumentoLegalFormOnce() {
    if (documentoLegalFormBooted) {
        return;
    }
    documentoLegalFormBooted = true;
    bootDocumentoLegalForm();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootDocumentoLegalFormOnce, { once: true });
} else {
    bootDocumentoLegalFormOnce();
}

window.addEventListener('pageshow', function () {
    bootDocumentoLegalFormOnce();
});

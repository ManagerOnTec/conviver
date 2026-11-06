// CHECAGEM ANEXOS
window.onload = function () {
    var fileInputs = document.querySelectorAll('input[type=file]');

    fileInputs.forEach(function (input) {
        var allowedExtensions = (input.dataset.allowedExtensions || 'jpg,jpeg,png')
            .split(',')
            .map(function (extension) {
                return extension.trim().toLowerCase();
            })
            .filter(Boolean);
        var maxFileSizeMb = Number(input.dataset.maxFileSizeMb || 5);

        // Aviso de substituição do Anexo
        input.addEventListener('click', function (e) {
            if (input.dataset.attachmentExisting === '1') {
                var confirmation = confirm('Atenção: Já existe um anexo, ao selecionar novo o antigo será substituído!');
                if (!confirmation) {
                    e.preventDefault();
                }
            }
        });

        // Tamanho máximo do arquivo e Tipo de arquivo
        input.addEventListener('change', function (e) {
            var file = e.target.files[0];

            if (file) {
                var fileExtension = file.name.split('.').pop().toLowerCase();
                var isValidFile = allowedExtensions.includes(fileExtension);

                if (!isValidFile) {
                    alert('Tipo de arquivo invalido. Somente imagens JPG, JPEG, PNG são permitidos, com tamanho maximo de 5 mb.');
                    e.target.value = ''; // limpar o campo de arquivo
                }
                else if (file.size > maxFileSizeMb * 1024 * 1024) {
                    alert('O arquivo excede o tamanho maximo permitido de 5 MB.');
                    e.target.value = ''; // limpar o campo de arquivo
                } else {
                    input.dataset.attachmentExisting = '0';
                }
            }
        });
    });
}
// FIM DA CHECAGEM DE ANEXOS
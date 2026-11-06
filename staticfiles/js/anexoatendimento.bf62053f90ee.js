// CHECAGEM ANEXOS
window.onload = function () {
    var fileInputs = document.querySelectorAll('input[type=file]');

    fileInputs.forEach(function (input) {

        // Aviso de substituição do Anexo
        input.addEventListener('click', function (e) {
            if (input.nextElementSibling && input.nextElementSibling.querySelector('span')) {
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
                var isValidFile = ['pdf', 'jpg', 'jpeg', 'png'].includes(fileExtension);

                if (!isValidFile) {
                    alert('Tipo de arquivo invalido. Somente arquivos PDF, JPG, JPEG, PNG são permitidos, com tamanho maximo de 5 mb.');
                    e.target.value = ''; // limpar o campo de arquivo
                }
                else if (file.size > 5 * 1024 * 1024) { // tamanho máximo de 5 MB
                    alert('O arquivo excede o tamanho maximo permitido de 5 MB.');
                    e.target.value = ''; // limpar o campo de arquivo
                }
            }
        });
    });
}
// FIM DA CHECAGEM DE ANEXOS
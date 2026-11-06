// INICIE O SCRIPT PARA INICIALIZAR O SELECT2
$(document).ready(function () {
    $('#id_pessoa').select2({
        language: {
            noResults: function () {
                return "Nenhum resultado encontrado. Por favor, tente novamente.";
            }
        }
    });
});
// FIM DO SCRIPT PARA INICIALIZAR O SELECT2

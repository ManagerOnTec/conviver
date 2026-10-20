var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

$(document).ready(function () {
    $(".update-fase").click(function () {
        var $btn = $(this);
        var adepId = $btn.data("adep-id");
        var newFase = $btn.data("new-fase");
        var acaoTexto = (newFase === 'A') ? "a ADMINISTRAÇÃO" : "a NÃO ADMINISTRAÇÃO";

        if (!confirm("Deseja confirmar " + acaoTexto + " deste medicamento?")) {
            return;
        }

        var $parentGroup = $btn.closest('.adep-action-buttons-group');
        $parentGroup.find('button').prop('disabled', true);
        var originalHtml = $btn.html();
        $btn.html('<i class="fas fa-spinner fa-spin me-1"></i> Gravando...');

        $.post("/prontuarios/adep_update_fase/" + adepId + "/" + newFase + "/", function (data) {
            if (data.success) {
                location.reload();
            } else {
                alert("Não foi possível atualizar: " + (data.error || "Erro desconhecido."));
                $parentGroup.find('button').prop('disabled', false);
                $btn.html(originalHtml);
            }
        }).fail(function () {
            alert("Erro de comunicação com o servidor. Tente novamente.");
            $parentGroup.find('button').prop('disabled', false);
            $btn.html(originalHtml);
        });
    });
});


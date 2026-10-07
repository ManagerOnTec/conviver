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
        var adepId = $(this).data("adep-id");
        var newFase = $(this).data("new-fase");
        $.post("/prontuarios/adep_update_fase/" + adepId + "/" + newFase + "/", function (data) {
            if (data.success) {
                alert("Resposta: Atualizado com sucesso!");
                location.reload();  // Recarrega a página
            } else {
                alert("Contate o administrador do sistema. " + data.error);
                location.reload();  // Recarrega a página
            }
        });
    });
});


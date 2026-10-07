$(document).ready(function () {
    $("#myInput").on("keyup", function () {
        var value = $(this).val().toLowerCase();
        $("#myList .col-lg-4").filter(function () {
            var card_title = $(this).find('.card-title').text().toLowerCase();
            $(this).toggle(card_title.indexOf(value) > -1);
        });
    });

    $(".btn-select-estabelecimento").on("click", function (e) {
        e.preventDefault();
        var estabelecimento_id = $(this).data("id");
        $("#selected-estabelecimento").val(estabelecimento_id);
        $("#btn-select-estabelecimento").click();
    });

    $("form").on("submit", function (e) {
        if ($("#myInput").is(":focus")) {
            e.preventDefault();
        }
    });

    // Código para mudar a cor do card ao passar o mouse
    $(".card").hover(
        function () {
            $(this).addClass("bg-primary-subtle");
        },
        function () {
            $(this).removeClass("bg-primary-subtle");
        }
    );
});
$(document).ready(function () {
    $("#myInput").on("keydown", function (event) {
        if (event.keyCode === 13) {
            event.preventDefault();
            return false;
        }
    });
    $("#myInput").on("keyup", function () {
        var value = $(this).val().toLowerCase();
        $("#myList .col-lg-4").filter(function () {
            var link_text = $(this).find('.card-title').text().toLowerCase();
            var link_value = $(this).find('a').attr('href');
            var match_text = link_text.indexOf(value) > -1;
            var match_value = link_value.indexOf(value) > -1;
            $(this).toggle(match_text || match_value);
        });
    });
    $(".card").hover(
        function () {
            $(this).addClass("bg-primary-subtle");
        },
        function () {
            $(this).removeClass("bg-primary-subtle");
        }
    );
});
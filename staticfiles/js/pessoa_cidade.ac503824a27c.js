(function ($) {
  $(function () {
    var $estado = $('#id_estado');
    var $cidade = $('#id_cidade');

    function atualizarCidades() {
      var estado_id = $estado.val();

      if (estado_id) {
        var url = '/admin/cadastros/cidade/?estado__id__exact=<estado_id>&_popup=1'

        $.ajax({
          url: url,
          dataType: 'html',
          success: function (data) {
            $cidade.html(data);
          }
        });
      } else {
        $cidade.empty();
      }
    }

    $estado.on('change', atualizarCidades);

    atualizarCidades();
  });
})(django.jQuery);
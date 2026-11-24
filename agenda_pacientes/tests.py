from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from .models import AgendaPaciente
from .views import AgendaPacienteDeleteView, AgendaPacienteRelatorioView


class AgendaPacienteDeleteViewTests(SimpleTestCase):
    def test_get_does_not_open_a_confirmation_screen(self):
        request = RequestFactory().get('/agenda/agenda_excluir/1/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            has_perms=lambda permissions: True,
        )
        request.session = {}

        response = AgendaPacienteDeleteView.as_view()(request, pk=1)

        self.assertEqual(response.status_code, 405)
        allowed_methods = response.headers['Allow'].split(', ')
        self.assertIn('POST', allowed_methods)
        self.assertNotIn('GET', allowed_methods)


class AgendaPacienteDownloadTests(SimpleTestCase):
    def test_download_uses_the_list_filters_and_returns_csv(self):
        queryset = MagicMock()
        queryset.select_related.return_value = queryset
        queryset.order_by.return_value = queryset
        queryset.filter.return_value = queryset
        instante = timezone.make_aware(datetime(2026, 11, 23, 12, 0))
        queryset.__iter__.return_value = iter([
            SimpleNamespace(
                pk=1,
                data_hora=instante,
                atendimento=SimpleNamespace(pessoa='Pessoa Teste'),
                atendimento_id=2,
                tipo='Consulta',
                exame=None,
                local=None,
                responsavel=None,
                efetuado='N',
                dt_efetuado=None,
                observacao='Retorno',
                get_status_display=lambda: 'Ativo',
                dt_registro=instante,
                us_registro=None,
            ),
        ])
        request = RequestFactory().get(
            '/agenda/agenda_relatorio/?tipo=4&efetuado=N')
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = {'estabelecimento_id': 3}

        with patch.object(AgendaPaciente.objects, 'filter',
                          return_value=queryset):
            response = AgendaPacienteRelatorioView().get(request)

        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="agenda_pacientes.csv"',
                      response['Content-Disposition'])
        self.assertIn(b'Pessoa Teste', response.content)
        self.assertIn(b'Retorno', response.content)
        self.assertTrue(any(
            call.kwargs.get('tipo_id') == 4
            for call in queryset.filter.call_args_list))
        self.assertTrue(any(
            call.kwargs.get('efetuado') == 'N'
            for call in queryset.filter.call_args_list))

from datetime import date, datetime
from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import PyPDF2

from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from admin_relatorios.models import (
    GerenciadorRelatorioGeral, GerenciadorRelatorioPersonalizado,
)
from .forms import AgendaPacienteFiltroForm, AgendaPacienteForm
from .models import AgendaPaciente, TipoAgendamento
from .views import (
    AgendaPacienteDeleteView,
    AgendaPacienteEfetuarView,
    AgendaPacienteRelatorioView,
    _aplicar_filtros,
    _dados_filtros_lista,
    _querystring_filtros,
)


class AgendaPacienteFormTests(SimpleTestCase):
    def test_schedule_note_is_required_in_form(self):
        form = AgendaPacienteForm()

        self.assertTrue(form.fields['observacao'].required)

    def test_exam_modal_requires_a_local_and_uses_friendly_error(self):
        from .forms import AgendaExameModalForm

        field = AgendaExameModalForm.base_fields['local']
        self.assertTrue(field.required)
        date_field = AgendaExameModalForm.base_fields['data_hora']
        self.assertTrue(date_field.required)
        date_field.error_messages['required'] = (
            'Informe a data e hora do agendamento.')
        self.assertEqual(
            date_field.error_messages['required'],
            'Informe a data e hora do agendamento.',
        )

    def test_public_form_can_hide_execution_fields(self):
        form = AgendaPacienteForm(ocultar_campos_execucao=True)

        self.assertNotIn('efetuado', form.fields)
        self.assertNotIn('dt_efetuado', form.fields)
        self.assertNotIn('observacao_execucao', form.fields)
        self.assertIn('status', form.fields)

    def test_execution_fields_remain_available_when_not_explicitly_hidden(self):
        form = AgendaPacienteForm()

        self.assertIn('efetuado', form.fields)
        self.assertIn('dt_efetuado', form.fields)
        self.assertIn('observacao_execucao', form.fields)


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


class AgendaPacienteFilterDefaultTests(SimpleTestCase):
    def test_initial_filter_defaults_to_today_and_can_be_changed(self):
        hoje = date(2026, 11, 24)
        request = RequestFactory().get('/agenda/agenda_listar/')
        request.session = {}

        with patch('agenda_pacientes.views.timezone.localdate',
                   return_value=hoje):
            filtros = _dados_filtros_lista(request)

        self.assertEqual(filtros['data_inicio'], hoje.isoformat())
        self.assertEqual(filtros['efetuado'], 'N')
        self.assertEqual(AgendaPacienteFiltroForm()['efetuado'].value(), 'N')
        queryset = MagicMock()
        queryset.filter.return_value = queryset
        _aplicar_filtros(queryset, filtros)
        self.assertEqual(queryset.filter.call_args_list, [
            call(efetuado='N'),
            call(data_hora__date__gte=hoje),
        ])

        request = RequestFactory().get(
            '/agenda/agenda_listar/?data_inicio=2026-11-20&efetuado=S')
        request.session = {}
        filtros = _dados_filtros_lista(request)

        self.assertEqual(filtros['data_inicio'], '2026-11-20')
        self.assertEqual(filtros['efetuado'], 'S')

    def test_all_effected_options_is_preserved_in_filter_querystring(self):
        request = RequestFactory().get(
            '/agenda/agenda_listar/?data_inicio=2026-11-20&efetuado=')
        request.session = {}
        filtros = _dados_filtros_lista(request)
        queryset = MagicMock()

        _, filtros_aplicados = _aplicar_filtros(queryset, filtros)

        self.assertEqual(filtros_aplicados['efetuado'], '')
        self.assertIn('efetuado=', _querystring_filtros(filtros_aplicados))
        self.assertFalse(any(
            chamada.kwargs.get('efetuado')
            for chamada in queryset.filter.call_args_list
        ))


class AgendaPacienteEfetuarViewTests(SimpleTestCase):
    def test_post_stores_execution_note_and_get_is_not_allowed(self):
        agenda = MagicMock(efetuado='N', exame_id=None)
        usuario = SimpleNamespace(is_authenticated=True)
        request = RequestFactory().post(
            '/agenda/agenda_efetuar/1/',
            {'observacao_execucao': '  Atendimento concluído.  '},
        )
        request.user = usuario
        request.session = {'estabelecimento_id': 3}
        request.META['HTTP_REFERER'] = '/agenda/agenda_listar/'

        with patch(
                'agenda_pacientes.views.get_object_or_404',
                return_value=agenda), \
                patch(
                    'agenda_pacientes.views.transaction.atomic',
                    return_value=nullcontext()), \
                patch('agenda_pacientes.views.messages.success'):
            response = AgendaPacienteEfetuarView().post(request, pk=1)

        agenda.efetuar.assert_called_once_with(
            usuario=usuario,
            observacao_execucao='Atendimento concluído.',
        )
        self.assertEqual(response.status_code, 302)

        get_request = RequestFactory().get('/agenda/agenda_efetuar/1/')
        get_request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            has_perms=lambda permissions: True,
        )
        get_request.session = {}
        get_response = AgendaPacienteEfetuarView.as_view()(
            get_request, pk=1)
        self.assertEqual(get_response.status_code, 405)


class AgendaPacienteExecutionModelTests(SimpleTestCase):
    def test_execution_note_is_saved_and_cleared_when_reopened(self):
        agenda = AgendaPaciente(efetuado='N')
        with patch.object(agenda, 'save') as salvar:
            agenda.efetuar(observacao_execucao='  Exame realizado.  ')

        self.assertEqual(agenda.observacao_execucao, 'Exame realizado.')
        self.assertIn(
            'observacao_execucao',
            salvar.call_args.kwargs['update_fields'],
        )

        agenda.efetuado = 'S'
        with patch.object(agenda, 'save'):
            agenda.efetuar(desfazer=True)
        self.assertEqual(agenda.observacao_execucao, '')


class AgendaPacienteAnnotationValidationTests(TestCase):
    def test_schedule_note_is_always_required(self):
        agenda = AgendaPaciente(efetuado='N')

        with self.assertRaises(ValidationError) as erro:
            agenda.full_clean()

        self.assertIn('observacao', erro.exception.message_dict)

    def test_execution_note_is_required_only_when_done(self):
        agenda = AgendaPaciente(
            efetuado='S',
            observacao='Anotação da agenda.',
        )

        with self.assertRaises(ValidationError) as erro:
            agenda.full_clean()

        self.assertIn('observacao_execucao', erro.exception.message_dict)
        agenda.efetuado = 'N'
        with self.assertRaises(ValidationError) as erro:
            agenda.full_clean()
        self.assertNotIn('observacao_execucao', erro.exception.message_dict)


class AgendaPacienteDownloadTests(SimpleTestCase):
    def test_report_uses_list_filters_and_returns_landscape_pdf(self):
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

        tipo_queryset = MagicMock()
        tipo_queryset.values_list.return_value.first.return_value = 'Exame'
        personalizado = SimpleNamespace(
            logo_header=None,
            dados_footer='Rodape configurado',
        )
        personalizado_queryset = MagicMock()
        personalizado_queryset.first.return_value = personalizado
        geral_queryset = MagicMock()
        geral_queryset.first.return_value = None
        with patch.object(
                AgendaPaciente.objects, 'filter', return_value=queryset), \
                patch.object(
                    TipoAgendamento.objects, 'filter',
                    return_value=tipo_queryset), \
                patch.object(
                    GerenciadorRelatorioPersonalizado.objects, 'filter',
                    return_value=personalizado_queryset) as filtro_personalizado, \
                patch.object(
                    GerenciadorRelatorioGeral.objects, 'filter',
                    return_value=geral_queryset):
            response = AgendaPacienteRelatorioView().get(request)

        filtro_personalizado.assert_called_once_with(
            relatorio='agenda_pacientes',
            estabelecimento_id=3,
            status='A',
        )
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="agenda_pacientes.pdf"',
                      response['Content-Disposition'])
        reader = PyPDF2.PdfReader(BytesIO(response.content))
        page = reader.pages[0]
        self.assertGreater(float(page.mediabox.width), float(page.mediabox.height))
        texto = page.extract_text()
        self.assertIn('Relatório de Agendas de Pacientes', texto)
        self.assertIn('Rodape configurado', texto)
        self.assertIn('Pessoa Teste', texto)
        for cabecalho in (
                'Data/Hora', 'Paciente', 'Tipo', 'Exame', 'Local',
                'Responsável'):
            self.assertIn(cabecalho, texto)
        self.assertNotIn('Retorno', texto)
        self.assertNotIn('Anotação agenda', texto)
        self.assertNotIn('Us. Registro', texto)
        self.assertNotIn('Dt. Registro', texto)
        self.assertNotIn('Data da execução', texto)
        self.assertNotIn('Atendimento', texto)
        self.assertTrue(any(
            call.kwargs.get('tipo_id') == 4
            for call in queryset.filter.call_args_list))
        self.assertTrue(any(
            call.kwargs.get('efetuado') == 'N'
            for call in queryset.filter.call_args_list))

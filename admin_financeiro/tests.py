from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from admin_financeiro.admin import (
    MovimentoBancarioAdmin, MovimentoConciliacaoFilter,
)
from admin_financeiro.models import MovimentoBancario


class MovimentoConciliacaoFilterTests(SimpleTestCase):
    def _filter(self, value):
        request = RequestFactory().get(
            '/admin/admin_financeiro/movimentobancario/',
            {'conciliacao': value})
        return request, MovimentoConciliacaoFilter(
            request, {'conciliacao': value}, MovimentoBancario, None)

    def test_filtra_movimentos_com_linha_conciliada(self):
        request, filtro = self._filter('conciliado')
        queryset = MovimentoBancario.objects.all()

        resultado = filtro.queryset(request, queryset)
        sql, params = resultado.query.sql_with_params()

        self.assertIn('status', sql)
        self.assertIn('C', params)

    def test_nao_conciliado_inclui_movimentos_sem_status_conciliado(self):
        request, filtro = self._filter('nao_conciliado')
        queryset = MovimentoBancario.objects.all()

        resultado = filtro.queryset(request, queryset)
        sql, params = resultado.query.sql_with_params()

        self.assertIn('NOT', sql.upper())
        self.assertIn('status', sql)
        self.assertIn('C', params)

    def test_lookup_de_data_hora_esta_disponivel_no_admin(self):
        model_admin = MovimentoBancarioAdmin(
            MovimentoBancario, admin.site)

        self.assertTrue(model_admin.lookup_allowed(
            'dt_registro__date__gte', '2025-02-01'))

"""Admin: importação de extrato e conciliação bancária."""
from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils import timezone
from django.shortcuts import redirect, render

from .models import MovimentoBancario, CompetenciaBancaria
from .models import ExtratoImportado, LinhaExtrato, ConciliacaoBancaria
from .extrato_parser import parse_arquivo


class ExtratoImportadoForm(forms.ModelForm):
    arquivo = forms.FileField(label='Arquivo do extrato (OFX ou PDF)')

    class Meta:
        model = ExtratoImportado
        fields = ['competencia_bancaria', 'arquivo']


@admin.register(ExtratoImportado)
class ExtratoImportadoAdmin(admin.ModelAdmin):
    form = ExtratoImportadoForm
    list_display = ['competencia_bancaria', 'tipo', 'dt_inicio', 'dt_fim',
                    'saldo_final_extrato', 'qtde_linhas', 'us_registro',
                    'dt_registro']
    list_filter = ['competencia_bancaria', 'tipo']
    readonly_fields = ['tipo', 'dt_inicio', 'dt_fim', 'saldo_final_extrato',
                       'dt_registro']

    def qtde_linhas(self, obj):
        return obj.linhas.count()
    qtde_linhas.short_description = 'Linhas importadas'

    def save_model(self, request, obj, form, change):
        # NÃO salva aqui: o arquivo é processado no save_related — mas o
        # ModelAdmin chama save_model antes de gravar o FileField? Não: o
        # FileField já vem preenchido no form. Salvamos o objeto e
        # processamos o arquivo em seguida (1ª importação apenas).
        if not change:
            obj.us_registro = request.user
        super().save_model(request, obj, form, change)
        if not change:
            self._processar(request, obj)

    def _processar(self, request, obj):
        """Lê o arquivo, cria as LinhaExtrato (dedupe por fitid) e a
        ConciliacaoBancaria da competência."""
        arquivo = obj.arquivo
        try:
            tipo, transacoes, saldo_final = parse_arquivo(
                arquivo.name, arquivo.read())
        except Exception as erro:
            messages.error(request, f'Falha ao ler o extrato: {erro}')
            return
        obj.tipo = tipo
        if transacoes:
            obj.dt_inicio = min(t['data'] for t in transacoes)
            obj.dt_fim = max(t['data'] for t in transacoes)
        obj.saldo_final_extrato = saldo_final
        obj.save(update_fields=['tipo', 'dt_inicio', 'dt_fim',
                                'saldo_final_extrato'])

        criadas = 0
        for t in transacoes:
            _, criada = LinhaExtrato.objects.get_or_create(
                extrato=obj, fitid=t['fitid'],
                defaults={'dt_lancamento': t['data'],
                          'valor': t['valor'],
                          'descricao': t['descricao'][:255],
                          'documento': t['documento']})
            criadas += 1 if criada else 0
        # Conciliação da competência (uma por competência).
        ConciliacaoBancaria.objects.get_or_create(
            competencia_bancaria=obj.competencia_bancaria,
            defaults={'us_registro': request.user if request else obj.us_registro,
                      'saldo_informado': saldo_final or 0,
                      'saldo_calculado': obj.competencia_bancaria.saldo_atual or 0})
        if request is not None:
            messages.success(
                request, f'Extrato importado: {criadas} linha(s) de '
                         f'{len(transacoes)} transação(eis). '
                         'Conclua a conciliação para fechar a competência.')

    # ---------- TELA DE CONCILIAÇÃO ----------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:extrato_id>/conciliar/',
                 self.admin_site.admin_view(self.conciliar_view),
                 name='admin_financeiro_conciliar'),
        ]
        return custom + urls

    def conciliar_view(self, request, extrato_id):
        """Tela de conciliação: linhas do extrato × movimentos da competência.

        Sugestão automática por (data + valor); o usuário marca conciliadas,
        ignora divergentes e pode LANÇAR o movimento direto da linha.
        """
        extrato = self.get_object(request, extrato_id)
        if extrato is None:
            messages.error(request, 'Extrato não encontrado.')
            return redirect('..')

        if request.method == 'POST':
            acao = request.POST.get('acao')
            if acao == 'sugerir':
                self._sugerir(extrato)
                messages.success(request, 'Sugestões recalculadas.')
            elif acao == 'conciliar':
                pks = request.POST.getlist('linhas')
                for linha in LinhaExtrato.objects.filter(
                        pk__in=pks, extrato=extrato):
                    self._conciliar_linha(
                        linha, request.POST.get(f'movimento_{linha.pk}'))
                messages.success(request, f'{len(pks)} linha(s) conciliada(s).')
            elif acao == 'ignorar':
                pks = request.POST.getlist('linhas')
                LinhaExtrato.objects.filter(
                    pk__in=pks, extrato=extrato).update(status='I')
                messages.success(request, f'{len(pks)} linha(s) ignorada(s).')
            elif acao == 'finalizar':
                return self._finalizar(request, extrato)
            return redirect(
                reverse('admin:admin_financeiro_conciliar',
                        args=[extrato.pk]))

        linhas = extrato.linhas.order_by('dt_lancamento', 'pk')
        # movimentos da competência ainda não ligados a nenhuma linha
        vinculados = LinhaExtrato.objects.exclude(
            movimento_bancario=None).values_list('movimento_bancario_id',
                                                 flat=True)
        movimentos = MovimentoBancario.objects.filter(
            competencia_bancaria=extrato.competencia_bancaria,
        ).exclude(pk__in=list(vinculados))

        conc, _ = ConciliacaoBancaria.objects.get_or_create(
            competencia_bancaria=extrato.competencia_bancaria,
            defaults={'us_registro': request.user,
                      'saldo_informado': extrato.saldo_final_extrato or 0})
        pendentes = extrato.linhas.exclude(status__in=['C', 'I']).count()
        # saldo calculado = saldo_anterior da competência + entradas − saídas
        saldo_calculado = extrato.competencia_bancaria.saldo_atual
        conc.saldo_calculado = saldo_calculado
        conc.divergencia = (conc.saldo_calculado or 0) - (conc.saldo_informado or 0)
        conc.save(update_fields=['saldo_calculado', 'divergencia'])

        context = dict(
            self.admin_site.each_context(request),
            title=f'Conciliação – {extrato.competencia_bancaria}',
            extrato=extrato, linhas=linhas, movimentos=movimentos,
            conciliacao=conc, pendentes=pendentes,
        )
        return render(request, 'admin_financeiro/conciliacao.html', context)

    # ------------------------------------------------------------------
    def _sugerir(self, extrato):
        """Casa linha ↔ movimento por (mesmo dia, mesmo valor)."""
        movs = list(MovimentoBancario.objects.filter(
            competencia_bancaria=extrato.competencia_bancaria,
            dt_movimento__isnull=False))
        for linha in extrato.linhas.filter(status='P'):
            valor_linha = linha.valor
            for mov in movs:
                valor_mov = mov.valor_entrada or 0
                if valor_mov == 0:
                    valor_mov = -(mov.valor_saida or 0)
                if mov.dt_movimento == linha.dt_lancamento \
                        and valor_mov == valor_linha \
                        and not LinhaExtrato.objects.filter(
                            movimento_bancario=mov, extrato=extrato).exists():
                    linha.movimento_bancario = mov
                    linha.status = 'C'
                    linha.save(update_fields=['movimento_bancario', 'status'])
                    break

    def _conciliar_linha(self, linha, movimento_id=None):
        if movimento_id:
            linha.movimento_bancario_id = movimento_id
        linha.status = 'C'
        linha.save()

    def _finalizar(self, request, extrato):
        conc, _ = ConciliacaoBancaria.objects.get_or_create(
            competencia_bancaria=extrato.competencia_bancaria,
            defaults={'us_registro': request.user,
                      'saldo_informado': extrato.saldo_final_extrato or 0})
        pendentes = extrato.linhas.exclude(status__in=['C', 'I']).count()
        if pendentes:
            messages.error(
                request,
                f'{pendentes} linha(s) ainda pendente(s): concilie ou '
                'ignore todas antes de finalizar.')
            return redirect(reverse('admin:admin_financeiro_conciliar',
                                    args=[extrato.pk]))
        conc.saldo_informado = extrato.saldo_final_extrato or 0
        conc.saldo_calculado = extrato.competencia_bancaria.saldo_atual
        conc.divergencia = (conc.saldo_calculado or 0) - (conc.saldo_informado or 0)
        if abs(conc.divergencia) >= Decimal('0.01'):
            messages.error(
                request,
                f'Divergência de R$ {conc.divergencia}: o saldo do sistema '
                'não confere com o extrato. Lance os movimentos que faltam.')
            return redirect(reverse('admin:admin_financeiro_conciliar',
                                    args=[extrato.pk]))
        conc.finalizada = True
        conc.dt_conciliacao = timezone.now()
        conc.save()
        messages.success(
            request, 'Conciliação FINALIZADA sem divergência. A competência '
                     'pode ser fechada.')
        return redirect(reverse('admin:admin_financeiro_conciliar',
                                args=[extrato.pk]))

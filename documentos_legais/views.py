import zipfile
from datetime import datetime
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, HttpResponseRedirect, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView
from django import forms
import django_filters
from django_filters import rest_framework as filters

from admin_cadastros.forms import PessoaDetailForm
from atendimentos.models import Atendimento
from dominios.choices import status_choices
from dominios.utils import CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, calcular_idade
from .forms import DocumentoLegalInternacaoForm
from .models import DocumentoLegalInternacao, ModeloDocumentoLegal, TipoDocumentoLegal
from .services import render_documento_html, atualizar_pdf_documento


def _listar_pdfs_para_download(pdf_paths):
    arquivos = []

    for pdf_path in pdf_paths:
        if not pdf_path:
            continue

        if not default_storage.exists(pdf_path) or default_storage.size(pdf_path) <= 0:
            continue

        with default_storage.open(pdf_path, 'rb') as arquivo_pdf:
            pdf_bytes = arquivo_pdf.read()

        if not pdf_bytes.startswith(b'%PDF'):
            continue

        arquivos.append((pdf_path.rsplit('/', 1)[-1], pdf_bytes))

    return arquivos


def _montar_resposta_download_pdfs(pdf_paths, download_name):
    arquivos = _listar_pdfs_para_download(pdf_paths)

    if not arquivos:
        return HttpResponse('Nenhum PDF valido encontrado para download.', status=404)

    if len(arquivos) == 1:
        nome_arquivo, pdf_bytes = arquivos[0]
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response

    pacote = BytesIO()
    nomes_usados = set()

    with zipfile.ZipFile(pacote, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for nome_arquivo, pdf_bytes in arquivos:
            nome_final = nome_arquivo
            contador = 1
            while nome_final in nomes_usados:
                base, ext = nome_arquivo.rsplit('.', 1)
                nome_final = f'{base}_{contador}.{ext}'
                contador += 1

            nomes_usados.add(nome_final)
            zip_file.writestr(nome_final, pdf_bytes)

    pacote.seek(0)
    response = HttpResponse(pacote.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{download_name}.zip"'
    return response


class DocumentoLegalFilter(filters.FilterSet):
    codigo_documento = django_filters.CharFilter(lookup_expr='icontains', label='Código')
    tipo_documento = django_filters.ModelChoiceFilter(
        queryset=TipoDocumentoLegal.objects.filter(status='A').order_by('ordem', 'nome'),
        label='Tipo de Termo',
    )
    responsavel_nome = django_filters.CharFilter(lookup_expr='icontains', label='Responsável')
    dt_assinatura = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        label='Dt. Assinatura',
    )
    status = django_filters.ChoiceFilter(choices=status_choices, label='Status')

    class Meta:
        model = DocumentoLegalInternacao
        fields = ['codigo_documento', 'tipo_documento', 'responsavel_nome', 'dt_assinatura', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class AtendimentoDocumentoLegalMixin(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin):
    model = DocumentoLegalInternacao
    required_tables = {
        'documentos_legais_tipodocumentolegal',
        'documentos_legais_modelodocumentolegal',
        'documentos_legais_documentolegalinternacao',
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not self._module_tables_ready():
            atendimento = self.get_atendimento()
            messages.warning(
                request,
                'O módulo de termos legais ainda não foi inicializado neste banco. Execute as migrações do sistema antes de usar esta tela.',
            )
            return HttpResponseRedirect(reverse('atendimento_detalhe', kwargs={'pk': atendimento.pk}))
        return super().dispatch(request, *args, **kwargs)

    def _module_tables_ready(self):
        existing_tables = set(connection.introspection.table_names())
        return self.required_tables.issubset(existing_tables)

    def _documentos_configurados(self):
        if hasattr(self, '_documentos_configurados_cache'):
            return self._documentos_configurados_cache

        estabelecimento = self.get_atendimento().estabelecimento
        tipos_ativos = TipoDocumentoLegal.objects.filter(status='A').exists()
        modelos_ativos = ModeloDocumentoLegal.objects.filter(status='A').filter(
            Q(estabelecimento=estabelecimento) | Q(estabelecimento__isnull=True)
        ).exists()
        self._documentos_configurados_cache = tipos_ativos and modelos_ativos
        return self._documentos_configurados_cache

    def get_atendimento(self):
        if hasattr(self, '_atendimento_cache'):
            return self._atendimento_cache

        atendimento_id = self.kwargs.get('atendimento_id')
        if not atendimento_id and getattr(self, 'object', None):
            atendimento_id = self.object.atendimento_id

        atendimento = get_object_or_404(
            Atendimento,
            pk=atendimento_id,
            estabelecimento_id=self.request.session.get('estabelecimento_id'),
        )
        self._atendimento_cache = atendimento
        return atendimento

    def get_success_url(self):
        return reverse_lazy('documentos_legais_listar', kwargs={'atendimento_id': self.get_atendimento().pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atendimento = self.get_atendimento()
        pessoa = atendimento.pessoa
        context['atendimento'] = atendimento
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(pessoa.dt_nascimento) if pessoa and pessoa.dt_nascimento else ' '
        context['titulo'] = 'Atendimentos'
        context['estabelecimento'] = atendimento.estabelecimento
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')
        context['documentos_legais_index'] = reverse_lazy('documentos_legais_listar', kwargs={'atendimento_id': atendimento.pk})
        context['detalhe_atendimento_url'] = reverse_lazy('atendimento_detalhe', kwargs={'pk': atendimento.pk})
        context['documentos_legais_configurados'] = self._documentos_configurados()
        return context


class DocumentoLegalListView(AtendimentoDocumentoLegalMixin, ListView):
    permission_required = 'documentos_legais.view_documentolegalinternacao'
    template_name = 'documentos_legais/documento_listar.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().filter(atendimento=self.get_atendimento()).select_related('tipo_documento', 'modelo_documento', 'us_registro')
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('documentos_legais_filters', None)
            params.clear()
        elif any(field in params for field in DocumentoLegalFilter.Meta.fields):
            self.request.session['documentos_legais_filters'] = params
        elif 'documentos_legais_filters' in self.request.session:
            params.update(self.request.session['documentos_legais_filters'])

        params.setdefault('status', 'A')
        self.filter = DocumentoLegalFilter(params, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'documentos_legais_listar'
        context['filter'] = self.filter
        context['has_filtered_pdfs'] = self.filter.qs.exclude(pdf_gerado='').filter(pdf_gerado__isnull=False).exists()
        return context


class DocumentoLegalFilteredPdfDownloadView(AtendimentoDocumentoLegalMixin, View):
    permission_required = 'documentos_legais.view_documentolegalinternacao'

    def get(self, request, *args, **kwargs):
        atendimento = self.get_atendimento()
        session_filters = request.session.get('documentos_legais_filters', {})
        filters_data = QueryDict('', mutable=True)
        filters_data.update(session_filters)
        filters_data['atendimento'] = atendimento.pk

        queryset = DocumentoLegalInternacao.objects.filter(atendimento=atendimento).select_related('tipo_documento', 'modelo_documento')
        filtered_objects = DocumentoLegalFilter(filters_data, queryset=queryset).qs
        pdf_paths = [documento.pdf_gerado.name for documento in filtered_objects if documento.pdf_gerado]

        return _montar_resposta_download_pdfs(
            pdf_paths,
            f'documentos_legais_atendimento_{atendimento.pk}_filtrados',
        )


class DocumentoLegalCreateView(AtendimentoDocumentoLegalMixin, CreateView):
    permission_required = 'documentos_legais.add_documentolegalinternacao'
    template_name = 'documentos_legais/documento_form.html'
    form_class = DocumentoLegalInternacaoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['atendimento'] = self.get_atendimento()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'documentos_legais_cadastrar'
        context['form_mode'] = 'create'
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if isinstance(response, HttpResponseRedirect):
            return response
        if not self._documentos_configurados():
            messages.warning(
                request,
                'Cadastre ao menos um tipo de termo e um modelo ativo no admin para gerar documentos legais.',
            )
        return response

    def form_valid(self, form):
        assinatura_funcionario_solicitada = form.cleaned_data.get('assinar_funcionario', False)
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.us_registro = self.request.user
            self.object.dt_assinatura = timezone.now()
            self.object.save()
            assinatura_funcionario_aplicada = atualizar_pdf_documento(
                self.object,
                user=self.request.user,
                assinar_funcionario=assinatura_funcionario_solicitada,
            )
        if assinatura_funcionario_solicitada and assinatura_funcionario_aplicada:
            messages.success(self.request, 'Documento legal gerado com sucesso e assinado digitalmente pelo funcionário!')
        elif assinatura_funcionario_solicitada:
            messages.warning(self.request, 'Documento legal gerado, mas a assinatura digital do funcionário não pôde ser aplicada.')
        else:
            messages.success(self.request, 'Documento legal gerado com sucesso!')
        return HttpResponseRedirect(self.get_success_url())


class DocumentoLegalDeleteView(AtendimentoDocumentoLegalMixin, DeleteView):
    permission_required = 'documentos_legais.delete_documentolegalinternacao'
    template_name = 'documentos_legais/documento_excluir.html'
    context_object_name = 'documento_legal'

    def post(self, request, *args, **kwargs):
        documento = self.get_object()
        codigo = documento.codigo_documento
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, f"Documento legal '{codigo}' excluído com sucesso.")
            return response
        except ProtectedError:
            messages.error(
                request,
                f"Erro ao excluir o documento legal '{codigo}'. O registro está protegido por referências a outros objetos.",
            )
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            messages.error(request, f"Erro ao excluir o documento legal '{codigo}': {str(e)}")
            return HttpResponseRedirect(self.get_success_url())


class DocumentoLegalPdfView(LoginRequiredMixin, CustomPermissionRequiredMixin, View):
    permission_required = 'documentos_legais.view_documentolegalinternacao'

    def _module_tables_ready(self):
        existing_tables = set(connection.introspection.table_names())
        return {
            'documentos_legais_tipodocumentolegal',
            'documentos_legais_modelodocumentolegal',
            'documentos_legais_documentolegalinternacao',
        }.issubset(existing_tables)

    def get(self, request, *args, **kwargs):
        if not self._module_tables_ready():
            messages.warning(
                request,
                'O módulo de termos legais ainda não foi inicializado neste banco. Execute as migrações do sistema antes de usar esta tela.',
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/')
        documento = get_object_or_404(
            DocumentoLegalInternacao,
            pk=kwargs['pk'],
            estabelecimento_id=request.session.get('estabelecimento_id'),
        )
        if not documento.pdf_gerado:
            raise Http404('PDF não encontrado para este documento.')
        return FileResponse(documento.pdf_gerado.open('rb'), content_type='application/pdf')


class DocumentoLegalTemplatePreviewView(LoginRequiredMixin, CustomPermissionRequiredMixin, View):
    permission_required = 'documentos_legais.add_documentolegalinternacao'

    def _module_tables_ready(self):
        existing_tables = set(connection.introspection.table_names())
        return {
            'documentos_legais_tipodocumentolegal',
            'documentos_legais_modelodocumentolegal',
            'documentos_legais_documentolegalinternacao',
        }.issubset(existing_tables)

    def get(self, request, *args, **kwargs):
        if not self._module_tables_ready():
            return JsonResponse({
                'modelos': [],
                'modelo_id': None,
                'titulo_documento': '',
                'html': '',
                'erro': 'O módulo de termos legais ainda não foi inicializado neste banco.',
            }, status=503)
        atendimento = get_object_or_404(
            Atendimento,
            pk=kwargs['atendimento_id'],
            estabelecimento_id=request.session.get('estabelecimento_id'),
        )
        tipo_id = request.GET.get('tipo_id')
        modelo_id = request.GET.get('modelo_id')

        modelos = ModeloDocumentoLegal.objects.filter(status='A', tipo_documento_id=tipo_id).filter(
            Q(estabelecimento=atendimento.estabelecimento) | Q(estabelecimento__isnull=True)
        ).select_related('tipo_documento', 'estabelecimento').order_by('-estabelecimento_id', 'nome_modelo')

        modelo = None
        if modelo_id:
            modelo = modelos.filter(pk=modelo_id).first()
        if modelo is None:
            modelo = modelos.first()

        html = render_documento_html(modelo, atendimento) if modelo else ''
        return JsonResponse({
            'modelos': [
                {
                    'id': item.id,
                    'nome': item.nome_modelo,
                    'exige_assinatura_responsavel': item.exige_assinatura_responsavel,
                    'exige_assinatura_atendente': item.exige_assinatura_atendente,
                }
                for item in modelos
            ],
            'modelo_id': modelo.id if modelo else None,
            'titulo_documento': modelo.titulo_documento if modelo else '',
            'html': html,
        })

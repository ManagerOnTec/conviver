from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from admin_cadastros.forms import PessoaDetailForm
from atendimentos.models import Atendimento
from dominios.utils import CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, calcular_idade
from .forms import DocumentoLegalInternacaoForm
from .models import DocumentoLegalInternacao, ModeloDocumentoLegal, TipoDocumentoLegal
from .services import build_document_context, render_documento_html, atualizar_pdf_documento


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
        queryset = super().get_queryset()
        return queryset.filter(atendimento=self.get_atendimento()).select_related('tipo_documento', 'modelo_documento', 'us_registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'documentos_legais_listar'
        return context


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
        context['preview_context'] = build_document_context(self.get_atendimento())
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


class DocumentoLegalUpdateView(AtendimentoDocumentoLegalMixin, UpdateView):
    permission_required = 'documentos_legais.change_documentolegalinternacao'
    template_name = 'documentos_legais/documento_form.html'
    form_class = DocumentoLegalInternacaoForm
    context_object_name = 'documento_legal'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['atendimento'] = self.get_atendimento()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'documentos_legais_editar'
        context['form_mode'] = 'update'
        context['preview_context'] = build_document_context(self.get_atendimento(), {
            'responsavel_nome': self.object.responsavel_nome,
            'responsavel_cpf': self.object.responsavel_cpf,
            'responsavel_documento': self.object.responsavel_documento,
            'responsavel_data_nascimento': self.object.responsavel_data_nascimento,
            'responsavel_telefone': self.object.responsavel_telefone,
            'responsavel_email': self.object.responsavel_email,
        })
        return context

    def form_valid(self, form):
        assinatura_funcionario_solicitada = form.cleaned_data.get('assinar_funcionario', False)
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.us_atualizacao = self.request.user
            self.object.dt_atualizacao = timezone.now()
            self.object.dt_assinatura = timezone.now()
            self.object.save()
            assinatura_funcionario_aplicada = atualizar_pdf_documento(
                self.object,
                user=self.request.user,
                assinar_funcionario=assinatura_funcionario_solicitada,
            )
        if assinatura_funcionario_solicitada and assinatura_funcionario_aplicada:
            messages.success(self.request, 'Documento legal atualizado com sucesso e assinado digitalmente pelo funcionário!')
        elif assinatura_funcionario_solicitada:
            messages.warning(self.request, 'Documento legal atualizado, mas a assinatura digital do funcionário não pôde ser aplicada.')
        else:
            messages.success(self.request, 'Documento legal atualizado com sucesso!')
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
            'modelos': [{'id': item.id, 'nome': item.nome_modelo} for item in modelos],
            'modelo_id': modelo.id if modelo else None,
            'titulo_documento': modelo.titulo_documento if modelo else '',
            'html': html,
        })

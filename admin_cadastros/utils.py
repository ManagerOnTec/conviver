from contas.models import Perfil
from django.contrib.admin import SimpleListFilter
from admin_cadastros.models import Estabelecimento


# extrair iniciais do nome de pessoa
def extrair_iniciais(nome):
    partes = nome.split()
    iniciais = [parte[0] for parte in partes if parte]
    return ".".join(iniciais)


# FILTRAR ESTABELECIMENTO PADRAO OU LIBERADOS PARA USAR NO ADMIN
class EstabelecimentoFilterAdminMixin(SimpleListFilter):
    title = 'Estabelecimento (Padrão)'
    parameter_name = 'estabelecimento'

    def lookups(self, request, model_admin):
        perfil = Perfil.objects.filter(user=request.user).first()
        if perfil:
            estabelecimentos = perfil.estabelecimento.all()
            # Assumindo que 'estabelecimento' é o campo para exibição
            return [(est.id, est.estabelecimento) for est in estabelecimentos]
        return []

    def _estabelecimento_ativo(self, request, perfil):
        """
        Estabelecimento ativo na sessão do usuário; se não houver sessão,
        usa o estabelecimento padrão do perfil.
        """
        estabelecimento_id = request.session.get('estabelecimento_id')
        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.filter(
                pk=estabelecimento_id).first()
            if estabelecimento is not None:
                return estabelecimento
        return getattr(perfil, 'estabelecimento_padrao', None)

    def queryset(self, request, queryset):
        perfil = Perfil.objects.filter(user=request.user).first()
        if not perfil and not request.user.is_superuser:
            return queryset.none()  # Se não há perfil, retorna queryset vazio

        if self.value():
            # Se o usuário estiver filtrando manualmente, aplica o filtro selecionado
            # (limitado ao que o perfil dele tem liberado).
            if perfil:
                return queryset.filter(
                    estabelecimento=self.value(),
                    estabelecimento__in=perfil.estabelecimento.all(),
                )
            return queryset.filter(estabelecimento=self.value())

        # Sem seleção manual: segue o estabelecimento ativo na sessão.
        estabelecimento = self._estabelecimento_ativo(request, perfil)

        if estabelecimento:
            # Filtra automaticamente pelo estabelecimento da sessão (ou padrão)
            return queryset.filter(estabelecimento=estabelecimento)

        if perfil is None:
            # Superuser sem perfil: não aplica restrição.
            return queryset

        # Se o perfil não tem um estabelecimento padrão, exibe todos os estabelecimentos associados
        return queryset.filter(estabelecimento__in=perfil.estabelecimento.all())

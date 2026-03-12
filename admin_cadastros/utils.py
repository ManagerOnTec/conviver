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

    def queryset(self, request, queryset):
        perfil = Perfil.objects.filter(user=request.user).first()
        if not perfil:
            return queryset.none()  # Se não há perfil, retorna queryset vazio

        if self.value():
            # Se o usuário estiver filtrando manualmente, aplica o filtro selecionado
            return queryset.filter(estabelecimento=self.value())

        if perfil.estabelecimento_padrao:
            # Filtra automaticamente pelo estabelecimento padrão do perfil do usuário
            return queryset.filter(estabelecimento=perfil.estabelecimento_padrao)

        # Se o perfil não tem um estabelecimento padrão, exibe todos os estabelecimentos associados
        return queryset.filter(estabelecimento__in=perfil.estabelecimento.all())
